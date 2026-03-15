"""Phase 2: Model training, walk-forward backtesting, and evaluation.

Prerequisites:
    Run Phase 1 first: python run_pipeline.py
    This creates data/processed/features.csv and data/processed/labels.csv

Usage:
    python run_training.py                          # Full walk-forward + eval
    python run_training.py --skip-walkforward       # Train single model only
    python run_training.py --calibration isotonic   # Calibration method
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_config
from src.evaluation.backtest import StrategyBacktest, format_backtest_report
from src.evaluation.metrics import (
    calibration_curve,
    evaluate_predictions,
    format_report,
)
from src.models.calibration import CalibratedModel
from src.models.explainability import SHAPExplainer
from src.models.trainer import TailRiskModel
from src.models.walk_forward import WalkForwardEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_processed_data(data_dir: str = "data/processed") -> tuple:
    """Load Phase 1 outputs.

    Returns:
        Tuple of (features, labels, continuous_target).
    """
    data_dir = Path(data_dir)

    features = pd.read_csv(
        data_dir / "features.csv", index_col="date", parse_dates=True
    )
    labels = pd.read_csv(
        data_dir / "labels.csv", index_col="date", parse_dates=True
    ).squeeze("columns")
    target = pd.read_csv(
        data_dir / "target_continuous.csv", index_col="date", parse_dates=True
    ).squeeze("columns")

    return features, labels, target


def main():
    parser = argparse.ArgumentParser(description="Tail Risk Gating - Phase 2 Training")
    parser.add_argument(
        "--skip-walkforward",
        action="store_true",
        help="Skip walk-forward, train single model on train/val split",
    )
    parser.add_argument(
        "--calibration",
        type=str,
        default="isotonic",
        choices=["isotonic", "platt"],
        help="Calibration method",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/processed",
        help="Directory with Phase 1 outputs",
    )
    args = parser.parse_args()

    config = load_config()
    output_dir = Path("data/model_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("TAIL RISK GATING SYSTEM - Phase 2 Training")
    logger.info("=" * 60)

    # Load Phase 1 data
    features, labels, continuous_target = load_processed_data(args.data_dir)
    logger.info(
        f"Loaded: {features.shape[0]} rows × {features.shape[1]} features"
    )
    logger.info(f"Positive rate: {labels.mean():.1%}")

    if args.skip_walkforward:
        # ── Simple train/val/test split ──
        train_end = config["model"]["train_end"]
        val_end = config["model"]["val_end"]

        X_train = features.loc[:train_end]
        y_train = labels.loc[:train_end]
        X_val = features.loc[train_end:val_end].iloc[1:]
        y_val = labels.loc[train_end:val_end].iloc[1:]
        X_test = features.loc[val_end:].iloc[1:]
        y_test = labels.loc[val_end:].iloc[1:]

        logger.info(
            f"Split — train: {len(X_train)}, val: {len(X_val)}, test: {len(X_test)}"
        )

        # Train
        model = TailRiskModel(config)
        model.fit(X_train, y_train, X_val, y_val)

        # Predict
        raw_probs_val = model.predict_proba(X_val)
        raw_probs_test = model.predict_proba(X_test)

        # Calibrate
        calibrator = CalibratedModel(method=args.calibration)
        calibrator.fit(raw_probs_val, y_val.values)
        cal_probs_test = calibrator.transform(raw_probs_test)

        # Evaluate
        raw_metrics = evaluate_predictions(y_test.values, raw_probs_test)
        cal_metrics = evaluate_predictions(y_test.values, cal_probs_test)

        logger.info("\n--- Raw Model ---")
        logger.info("\n" + format_report(raw_metrics))
        logger.info("\n--- Calibrated Model ---")
        logger.info("\n" + format_report(cal_metrics))

        # SHAP
        explainer = SHAPExplainer(model)
        shap_values = explainer.compute(X_test)
        importance = explainer.global_importance(shap_values, X_test)

        logger.info("\nTop 10 features (SHAP):")
        for feat, val in importance.head(10).items():
            logger.info(f"  {feat}: {val:.4f}")

        explainer.save_values(shap_values, X_test, output_dir / "shap_values.csv")
        model.save(output_dir / "model_single.joblib")

        predictions = pd.Series(cal_probs_test, index=X_test.index)
        actuals = y_test
        fwd_returns = continuous_target.loc[X_test.index]

    else:
        # ── Walk-forward backtesting ──
        engine = WalkForwardEngine(config)
        wf_result = engine.run(features, labels)

        predictions = wf_result.predictions
        actuals = wf_result.actuals

        # Evaluate raw walk-forward predictions
        raw_metrics = evaluate_predictions(actuals.values, predictions.values)
        logger.info("\n--- Walk-Forward Results (Raw) ---")
        logger.info("\n" + format_report(raw_metrics))

        # Calibrate using first half of OOS predictions as calibration set
        mid = len(predictions) // 2
        cal_probs = predictions.copy()
        cal_idx = predictions.index[:mid]
        test_idx = predictions.index[mid:]

        calibrator = CalibratedModel(method=args.calibration)
        calibrator.fit(predictions.iloc[:mid].values, actuals.iloc[:mid].values)
        cal_probs.iloc[mid:] = calibrator.transform(predictions.iloc[mid:].values)

        cal_metrics = evaluate_predictions(
            actuals.iloc[mid:].values, cal_probs.iloc[mid:].values
        )
        logger.info("\n--- Walk-Forward Results (Calibrated, 2nd half) ---")
        logger.info("\n" + format_report(cal_metrics))

        # SHAP on last fold's model
        last_model = wf_result.models[-1]
        # Use last fold's test period for SHAP
        last_fold = wf_result.fold_stats[-1]
        shap_start = last_fold["test_start"]
        shap_end = last_fold["test_end"]
        X_shap = features.loc[shap_start:shap_end]

        explainer = SHAPExplainer(last_model)
        shap_values = explainer.compute(X_shap)
        importance = explainer.global_importance(shap_values, X_shap)

        logger.info("\nTop 10 features (SHAP, last fold):")
        for feat, val in importance.head(10).items():
            logger.info(f"  {feat}: {val:.4f}")

        explainer.save_values(shap_values, X_shap, output_dir / "shap_values.csv")

        # Save walk-forward predictions
        predictions.to_csv(output_dir / "wf_predictions.csv")
        actuals.to_csv(output_dir / "wf_actuals.csv")

        fwd_returns = continuous_target.reindex(predictions.index).dropna()
        predictions = predictions.loc[fwd_returns.index]
        actuals = actuals.loc[fwd_returns.index]

        # Save fold stats
        fold_df = pd.DataFrame(wf_result.fold_stats)
        fold_df.to_csv(output_dir / "fold_stats.csv", index=False)

    # ── Strategy backtest ──
    bt = StrategyBacktest(config)
    bt_results = bt.run(predictions, actuals, fwd_returns)
    bt_results.to_csv(output_dir / "backtest_results.csv", index=False)

    logger.info("\n" + format_backtest_report(bt_results))

    # Save calibration curve
    cal_curve = calibration_curve(actuals.values, predictions.values)
    cal_curve.to_csv(output_dir / "calibration_curve.csv", index=False)

    logger.info(f"\nAll outputs saved to {output_dir}/")
    logger.info("Phase 2 complete.")


if __name__ == "__main__":
    main()
