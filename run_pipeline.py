"""Main script to run Phase 1: fetch data, build features, compute labels.

Usage:
    python run_pipeline.py                    # Fetch fresh data + build features
    python run_pipeline.py --use-cache        # Use cached data
    python run_pipeline.py --threshold -0.10  # Custom loss threshold
    python run_pipeline.py --horizon 10       # Custom horizon (10 trading days)
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.data.db import build_store
from src.data.fetcher import DataFetcher
from src.features.pipeline import FeaturePipeline
from src.labels.strategy import compute_labels

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Tail Risk Gating - Phase 1 Pipeline")
    parser.add_argument(
        "--use-cache", action="store_true", help="Use cached data instead of fetching"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Disable PostgreSQL reads/writes even if configured",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Loss threshold (e.g., -0.15 for -15%%)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=None,
        help="Forward-looking horizon in trading days",
    )
    args = parser.parse_args()

    # Load config
    config = load_config()
    threshold = args.threshold or config["strategy"]["default_threshold"]
    horizon = args.horizon or config["strategy"]["default_horizon"]
    store = None if args.no_db else build_store(config)

    logger.info("=" * 60)
    logger.info("TAIL RISK GATING SYSTEM - Phase 1 Pipeline")
    logger.info(f"  Threshold: {threshold:.1%}")
    logger.info(f"  Horizon: {horizon} trading days")
    logger.info(f"  PostgreSQL: {'enabled' if store else 'disabled'}")
    logger.info("=" * 60)

    # Step 1: Get data
    fetcher = DataFetcher(config, store=store)
    if args.use_cache:
        logger.info("Loading cached data...")
        raw_data = fetcher.load_cached()
    else:
        logger.info("Fetching fresh data...")
        raw_data = fetcher.fetch_all()

    if not raw_data:
        logger.error("No data available. Check your internet connection or cache.")
        sys.exit(1)

    # Step 2: Build features
    pipeline = FeaturePipeline(config)
    features = pipeline.build(raw_data)

    # Step 3: Compute labels
    spy_close = raw_data["spy"]["Close"] if isinstance(raw_data["spy"], pd.DataFrame) else raw_data["spy"]
    vix_close = raw_data["vix"]["Close"] if isinstance(raw_data["vix"], pd.DataFrame) else raw_data["vix"]

    labels, continuous_target = compute_labels(
        spy_close=spy_close,
        vix=vix_close,
        horizon=horizon,
        threshold=threshold,
        method="realized_move",
    )

    # Step 4: Align features and labels
    # Use inner join on dates
    common_idx = features.index.intersection(labels.dropna().index)
    features_aligned = features.loc[common_idx]
    labels_aligned = labels.loc[common_idx]
    target_aligned = continuous_target.loc[common_idx]

    # Drop rows with NaN features (from rolling window warmup)
    valid_mask = features_aligned.notna().all(axis=1)
    features_final = features_aligned[valid_mask]
    labels_final = labels_aligned[valid_mask]
    target_final = target_aligned[valid_mask]

    logger.info("")
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Final dataset: {features_final.shape[0]} rows × {features_final.shape[1]} features")
    logger.info(f"  Date range: {features_final.index.min()} to {features_final.index.max()}")
    logger.info(f"  Positive labels: {labels_final.sum()} ({labels_final.mean():.1%})")
    logger.info(f"  Feature columns: {list(features_final.columns)}")
    logger.info("=" * 60)

    # Save processed data
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    features_final.to_csv(output_dir / "features.csv")
    labels_final.to_csv(output_dir / "labels.csv", header=True)
    target_final.to_csv(output_dir / "target_continuous.csv", header=True)

    logger.info(f"Saved processed data to {output_dir}/")

    # Print a quick summary table
    logger.info("")
    logger.info("Feature summary statistics:")
    logger.info(features_final.describe().round(4).to_string())


if __name__ == "__main__":
    main()
