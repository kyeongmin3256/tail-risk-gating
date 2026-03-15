"""Phase 2: Train model, walk-forward backtest, SHAP explainability.

Loads Phase 1 processed data, trains LightGBM with walk-forward
backtesting, calibrates probabilities, runs SHAP, and evaluates
gated vs ungated strategy performance.

Usage:
    python run_model.py                      # Full Phase 2 pipeline
    python run_model.py --skip-shap          # Skip SHAP (faster)
    python run_model.py --gate-threshold 0.2 # Custom gating threshold
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_config
from src.evaluation.backtest import StrategyBacktest, print_backtest_report
from src.evaluation.metrics import evaluate_model, print_evaluation_report
from src.models.calibration import CalibratedModel
from src.models.explainability import SHAPExplainer
from src.models.trainer import TailRiskModel
from src.models.walk_forward import WalkForwardBacktest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_processed_data(data_dir: str = "data/processed") -> tuple:
    """Load Phase 1 processed data.

    Returns:
        Tuple of (features, labels, continuous_target).
    """
    data_path = Path(data_dir)
    features = pd.read_csv(data_path / "features.csv", index_col="date", parse_dates=True)
    labels = pd.read_csv(data_path / "labels.csv", index_col="date", parse_dates=True).squeeze()
    target = pd.read_csv(data_path / "target_continuous.csv", index_col="date", parse_dates=True).squeeze()
    return features, labels, target


def main():
    parser = argparse.ArgumentParser(description="Tail Risk Gating - Phase 2 Model Pipeline")
    parser.add_argument("--skip-shap", action="store_true", help="Skip SHAP computation")
    parser.add_argument(
        "--gate-threshold", type=float, default=0.3,
        help="Probability threshold for gating trades (default: 0.3)",
    )
    args = parser.parse_args()

    config = load_config()
    output_dir = Path("data/model_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("TAIL RISK GATING SYSTEM - Phase 2: Model Pipeline")
    logger.info("=" * 60)

    # ── Step 1: Load data ─────────────────────────────────────
    logger.info("Loading processed data...")
    features, labels, continuous_target = load_processed_data()
    logger.info(f"  {features.shape[0]} samples, {features.shape[1]} features")
    logger.info(f"  Positive rate: {labels.mean():.1%}")

    # ── Step 2: Walk-forward backtest ─────────────────────────
    logger.info("\nRunning walk-forward backtesting...")
    wf = WalkForwardBacktest(config)
    wf_result = wf.run(features, labels)

    # Collect out-of-sample predictions
    oos_preds = wf_result.all_predictions
    oos_actuals = wf_result.all_actuals

    logger.info(f"\nOut-of-sample predictions: {len(oos_preds)} samples across {wf_result.n_folds} folds")

    # Save OOS predictions
    oos_df = pd.DataFrame({
        "prediction": oos_preds,
        "actual": oos_actuals,
    })
    oos_df.to_csv(output_dir / "oos_predictions.csv")

    # ── Step 3: Evaluate (pre-calibration) ────────────────────
    logger.info("\n--- Pre-Calibration Evaluation ---")
    pre_metrics = evaluate_model(oos_actuals.values, oos_preds.values)
    print_evaluation_report(pre_metrics)

    # ── Step 4: Calibrate probabilities ───────────────────────
    logger.info("\nCalibrating probabilities (Platt scaling)...")
    calibrator = CalibratedModel(method="sigmoid")
    calibrated_preds = calibrator.fit_transform(oos_preds.values, oos_actuals.values)
    calibrated_series = pd.Series(calibrated_preds, index=oos_preds.index)

    logger.info("\n--- Post-Calibration Evaluation ---")
    post_metrics = evaluate_model(oos_actuals.values, calibrated_preds)
    print_evaluation_report(post_metrics)

    # Save calibrated predictions
    cal_df = pd.DataFrame({
        "raw_prediction": oos_preds,
        "calibrated_prediction": calibrated_series,
        "actual": oos_actuals,
    })
    cal_df.to_csv(output_dir / "calibrated_predictions.csv")

    # ── Step 5: SHAP explainability ───────────────────────────
    if not args.skip_shap:
        logger.info("\nComputing SHAP values (using last fold model)...")
        last_model = wf_result.folds[-1].model
        explainer = SHAPExplainer(last_model)

        # Compute SHAP on the last fold's test set
        last_fold = wf_result.folds[-1]
        X_explain = features.loc[last_fold.test_index]
        shap_values = explainer.compute(X_explain)

        # Feature importance
        top = explainer.top_features(shap_values, list(features.columns), n=15)
        logger.info(f"\nTop features by SHAP importance:\n{top.to_string()}")
        top.to_csv(output_dir / "shap_feature_importance.csv")

        # Save full SHAP values
        explainer.save_values(
            shap_values, list(features.columns),
            last_fold.test_index, output_dir / "shap_values.csv",
        )
    else:
        logger.info("\nSkipping SHAP (--skip-shap flag).")

    # ── Step 6: Train final model on all data ─────────────────
    logger.info("\nTraining final model on full dataset...")
    final_model = TailRiskModel(config)
    split_idx = int(len(features) * 0.85)
    X_train_final = features.iloc[:split_idx]
    y_train_final = labels.iloc[:split_idx]
    X_val_final = features.iloc[split_idx:]
    y_val_final = labels.iloc[split_idx:]
    final_model.fit(X_train_final, y_train_final, X_val_final, y_val_final)

    # Feature importance from final model
    fi = final_model.get_feature_importance()
    fi.to_csv(output_dir / "feature_importance_gain.csv")
    logger.info(f"\nFinal model feature importance (gain):\n{fi.head(10).to_string()}")

    # ── Step 7: Strategy backtest ─────────────────────────────
    logger.info("\nRunning strategy backtest...")
    # Align continuous target with OOS predictions
    common = calibrated_series.index.intersection(continuous_target.index)
    bt = StrategyBacktest(
        predictions=calibrated_series.loc[common],
        actuals=oos_actuals.loc[common],
        continuous_pnl=continuous_target.loc[common],
    )

    # Single threshold
    comparison = bt.compare(gate_threshold=args.gate_threshold)
    print_backtest_report(comparison)

    # Multiple thresholds
    multi = bt.compare_multiple_thresholds([0.1, 0.2, 0.3, 0.4, 0.5])
    multi.to_csv(output_dir / "backtest_comparison.csv", index=False)

    # ── Done ──────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2 COMPLETE")
    logger.info(f"  All outputs saved to {output_dir}/")
    logger.info(f"  Files: {[f.name for f in output_dir.glob('*')]}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
