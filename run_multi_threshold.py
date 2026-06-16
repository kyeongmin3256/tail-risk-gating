"""Multi-threshold training: train separate models for -2%, -4%, -6%, -8% loss thresholds.

For each threshold, this script:
  1. Recomputes binary labels using the given threshold
  2. Runs walk-forward training (LightGBM + calibration)
  3. Computes SHAP feature importance
  4. Runs gated vs ungated backtest
  5. Saves all outputs to outputs/threshold_{N}/

Prerequisites:
    python run_pipeline.py --use-cache   # features must exist in data/processed/
    (raw cache must exist in data/raw/ for spy and vix)

Usage:
    python run_multi_threshold.py
    python run_multi_threshold.py --thresholds -0.02 -0.04 -0.06 -0.08
    python run_multi_threshold.py --calibration platt
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.evaluation.backtest import StrategyBacktest, format_backtest_report
from src.evaluation.metrics import calibration_curve, evaluate_predictions, format_report
from src.labels.strategy import compute_labels
from src.models.calibration import CalibratedModel
from src.models.explainability import SHAPExplainer
from src.models.walk_forward import WalkForwardEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = [-0.02, -0.04, -0.06, -0.08]


def output_dir_for(threshold: float) -> Path:
    """Return output directory path for a given threshold.

    e.g. threshold=-0.04 → outputs/threshold_-4
    """
    pct = int(round(threshold * 100))
    return Path(f"outputs/threshold_{pct}")


def load_features() -> pd.DataFrame:
    """Load precomputed features from Phase 1."""
    path = Path("data/processed/features.csv")
    if not path.exists():
        logger.error(
            "data/processed/features.csv not found. "
            "Run: python run_pipeline.py --use-cache"
        )
        sys.exit(1)
    return pd.read_csv(path, index_col="date", parse_dates=True)


def load_raw_price_series() -> tuple[pd.Series, pd.Series]:
    """Load SPY close and VIX close from raw cache for label computation."""
    spy_path = Path("data/raw/spy.csv")
    vix_path = Path("data/raw/vix.csv")

    if not spy_path.exists() or not vix_path.exists():
        logger.error(
            "Raw cache not found (data/raw/spy.csv or data/raw/vix.csv). "
            "Run: python run_pipeline.py to fetch and cache data."
        )
        sys.exit(1)

    spy = pd.read_csv(spy_path, index_col="date", parse_dates=True)["Close"]
    vix = pd.read_csv(vix_path, index_col="date", parse_dates=True)["Close"]
    return spy, vix


def run_threshold(
    threshold: float,
    features: pd.DataFrame,
    spy_close: pd.Series,
    vix_close: pd.Series,
    config: dict,
    calibration_method: str,
) -> None:
    """Run the full training and evaluation pipeline for one threshold."""
    pct_label = f"{threshold:.0%}"
    out_dir = output_dir_for(threshold)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"THRESHOLD: {pct_label}  →  {out_dir}")
    logger.info("=" * 60)

    # ── Step 1: Compute labels for this threshold ──────────────────
    horizon = config["strategy"]["default_horizon"]
    labels, continuous_target = compute_labels(
        spy_close=spy_close,
        vix=vix_close,
        horizon=horizon,
        threshold=threshold,
        method="realized_move",
    )

    # ── Step 2: Align features + labels (drop NaN rows) ───────────
    common_idx = features.index.intersection(labels.dropna().index)
    feat = features.loc[common_idx]
    lab = labels.loc[common_idx]
    target = continuous_target.loc[common_idx]

    valid = feat.notna().all(axis=1)
    feat = feat[valid]
    lab = lab[valid]
    target = target[valid]

    logger.info(f"Dataset: {len(feat)} rows, positive rate: {lab.mean():.1%}")

    # ── Step 3: Walk-forward training ─────────────────────────────
    engine = WalkForwardEngine(config)
    wf_result = engine.run(feat, lab)

    predictions = wf_result.predictions
    actuals = wf_result.actuals

    raw_metrics = evaluate_predictions(actuals.values, predictions.values)
    logger.info(f"\n--- Walk-Forward Results (Raw) [{pct_label}] ---")
    logger.info("\n" + format_report(raw_metrics))

    # ── Step 4: Calibration ────────────────────────────────────────
    mid = len(predictions) // 2
    cal_probs = predictions.copy()
    calibrator = CalibratedModel(method=calibration_method)
    calibrator.fit(predictions.iloc[:mid].values, actuals.iloc[:mid].values)
    cal_probs.iloc[mid:] = calibrator.transform(predictions.iloc[mid:].values)

    cal_metrics = evaluate_predictions(
        actuals.iloc[mid:].values, cal_probs.iloc[mid:].values
    )
    logger.info(f"\n--- Walk-Forward Results (Calibrated, 2nd half) [{pct_label}] ---")
    logger.info("\n" + format_report(cal_metrics))

    # ── Step 5: SHAP (last fold) ───────────────────────────────────
    last_model = wf_result.models[-1]
    last_fold = wf_result.fold_stats[-1]
    X_shap = feat.loc[last_fold["test_start"]:last_fold["test_end"]]

    explainer = SHAPExplainer(last_model)
    shap_values = explainer.compute(X_shap)
    importance = explainer.global_importance(shap_values, X_shap)

    logger.info(f"\nTop 10 features (SHAP, last fold) [{pct_label}]:")
    for feat_name, val in importance.head(10).items():
        logger.info(f"  {feat_name}: {val:.4f}")

    # ── Step 6: Backtest ───────────────────────────────────────────
    fwd_returns = target.reindex(predictions.index).dropna()
    preds_bt = predictions.loc[fwd_returns.index]
    actuals_bt = actuals.loc[fwd_returns.index]

    bt = StrategyBacktest(config)
    bt_results = bt.run(preds_bt, actuals_bt, fwd_returns)
    primary_results = bt.run_primary(
        cal_probs.loc[fwd_returns.index],
        actuals_bt,
        fwd_returns,
        threshold_pct=abs(int(round(threshold * 100))),
    )
    logger.info("\n" + format_backtest_report(bt_results))
    logger.info("\n" + format_backtest_report(primary_results))

    # ── Step 7: Save outputs ───────────────────────────────────────
    predictions.to_csv(out_dir / "wf_predictions.csv")
    actuals.to_csv(out_dir / "wf_actuals.csv")
    cal_probs.to_csv(out_dir / "wf_predictions_calibrated.csv")

    pd.DataFrame(wf_result.fold_stats).to_csv(out_dir / "fold_stats.csv", index=False)
    bt_results.to_csv(out_dir / "backtest_results.csv", index=False)
    primary_results.to_csv(out_dir / "gating_primary.csv", index=False)

    cal_curve = calibration_curve(actuals.values, predictions.values)
    cal_curve.to_csv(out_dir / "calibration_curve.csv", index=False)

    explainer.save_values(shap_values, X_shap, out_dir / "shap_values.csv")

    # Save summary metrics
    summary = {
        "threshold": threshold,
        "positive_rate": lab.mean(),
        "n_samples": len(lab),
        **{f"raw_{k}": v for k, v in raw_metrics.items() if isinstance(v, float)},
        **{f"cal_{k}": v for k, v in cal_metrics.items() if isinstance(v, float)},
    }
    pd.Series(summary).to_csv(out_dir / "summary.csv", header=False)

    logger.info(f"All outputs saved to {out_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Train models for multiple loss thresholds"
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=DEFAULT_THRESHOLDS,
        help="Loss thresholds to train (e.g., -0.02 -0.04 -0.06 -0.08)",
    )
    parser.add_argument(
        "--calibration",
        type=str,
        default="isotonic",
        choices=["isotonic", "platt"],
        help="Calibration method",
    )
    args = parser.parse_args()

    config = load_config()

    logger.info("=" * 60)
    logger.info("MULTI-THRESHOLD TRAINING")
    logger.info(f"  Thresholds: {[f'{t:.0%}' for t in args.thresholds]}")
    logger.info(f"  Calibration: {args.calibration}")
    logger.info("=" * 60)

    # Load shared inputs once
    features = load_features()
    spy_close, vix_close = load_raw_price_series()

    logger.info(f"Features: {features.shape[0]} rows × {features.shape[1]} columns")

    for threshold in args.thresholds:
        run_threshold(
            threshold=threshold,
            features=features,
            spy_close=spy_close,
            vix_close=vix_close,
            config=config,
            calibration_method=args.calibration,
        )

    logger.info("")
    logger.info("=" * 60)
    logger.info("ALL THRESHOLDS COMPLETE")
    for t in args.thresholds:
        logger.info(f"  {t:.0%}  →  {output_dir_for(t)}/")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
