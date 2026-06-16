#!/usr/bin/env python3
"""Refresh gating_primary.csv for each threshold using calibrated predictions."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.evaluation.backtest import StrategyBacktest

THRESHOLDS = [2, 4, 6, 8]


def main() -> None:
    root = ROOT
    config = load_config()
    fwd = pd.read_csv(
        root / "data/processed/target_continuous.csv",
        index_col="date",
        parse_dates=True,
    ).squeeze()

    bt = StrategyBacktest(config)
    for t in THRESHOLDS:
        out_dir = root / f"outputs/threshold_-{t}"
        if not out_dir.exists():
            print(f"skip missing {out_dir}")
            continue

        preds = pd.read_csv(
            out_dir / "wf_predictions_calibrated.csv",
            index_col=0,
            parse_dates=True,
        ).squeeze()
        actuals = pd.read_csv(
            out_dir / "wf_actuals.csv",
            index_col=0,
            parse_dates=True,
        ).squeeze()
        fwd_aligned = fwd.reindex(preds.index).dropna()
        preds = preds.loc[fwd_aligned.index]
        actuals = actuals.loc[fwd_aligned.index]

        primary = bt.run_primary(preds, actuals, fwd_aligned, threshold_pct=t)
        primary.to_csv(out_dir / "gating_primary.csv", index=False)
        print(f"wrote {out_dir / 'gating_primary.csv'}")


if __name__ == "__main__":
    main()
