#!/usr/bin/env python3
"""Refresh README Core Results from gating artifacts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.evaluation.gating import STRADDLE_BH_LABEL, apply_gating, gating_config_for

START = "<!-- METRICS:START -->"
END = "<!-- METRICS:END -->"


def _sharpe(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))


def _cvar95(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) == 0:
        return 0.0
    q = r.quantile(0.05)
    tail = r[r <= q]
    return float(tail.mean()) if len(tail) else float(q)


def _pct_change(before: float, after: float) -> float:
    if before == 0:
        return 0.0
    return (after - before) / abs(before) * 100.0


def _risk_reduction(before: float, after: float) -> float:
    if before == 0:
        return 0.0
    return (abs(before) - abs(after)) / abs(before) * 100.0


def summarize_threshold(
    threshold: int,
    fwd: pd.Series,
    config: dict,
) -> dict:
    cfg = gating_config_for(threshold, config)
    mode = str(cfg["mode"])
    gate = float(cfg["gate_threshold"])
    preds = pd.read_csv(
        ROOT / f"outputs/threshold_-{threshold}/wf_predictions_calibrated.csv",
        index_col=0,
        parse_dates=True,
    ).squeeze()
    common = preds.index.intersection(fwd.index)
    p = preds.loc[common]
    base = fwd.loc[common]
    gated = apply_gating(base, p, gate, mode)

    sharpe_u = _sharpe(base)
    sharpe_g = _sharpe(gated)
    cvar_u = _cvar95(base)
    cvar_g = _cvar95(gated)

    primary_path = ROOT / f"outputs/threshold_-{threshold}/gating_primary.csv"
    days_gated = int((gated == 0).sum())
    if primary_path.exists():
        primary = pd.read_csv(primary_path)
        gated_row = primary[primary["strategy"] != STRADDLE_BH_LABEL].iloc[0]
        days_gated = int(gated_row.get("days_skipped", days_gated))

    return {
        "threshold": threshold,
        "mode": mode,
        "gate_threshold": gate,
        "sharpe_ungated": sharpe_u,
        "sharpe_gated": sharpe_g,
        "sharpe_pct": _pct_change(sharpe_u, sharpe_g),
        "cvar_ungated": cvar_u,
        "cvar_gated": cvar_g,
        "cvar_reduction_pct": _risk_reduction(cvar_u, cvar_g),
        "days_gated": days_gated,
    }


def build_metrics_block(config: dict) -> str:
    fwd = pd.read_csv(
        ROOT / "data/processed/target_continuous.csv",
        index_col="date",
        parse_dates=True,
    ).squeeze()

    headline = summarize_threshold(4, fwd, config)
    best = summarize_threshold(2, fwd, config)

    oot_path = ROOT / "data/model_outputs/significance_oot_t2_soft.csv"
    oot_line = ""
    if oot_path.exists():
        oot = pd.read_csv(oot_path)
        best_oot = oot.loc[oot["gate_threshold"] == 0.2]
        if len(best_oot):
            row = best_oot.iloc[0]
            oot_line = (
                f"- OOT soft gate (-2% @ 20%, last 756 days): Sharpe delta "
                f"`{row['sharpe_diff']:+.4f}` · CVaR improvement `{row['cvar_improvement']:.5f}`"
            )

    return f"""{START}
### Walk-forward gated vs Short Straddle B&H (-4% model bucket, {headline['mode']} @ {headline['gate_threshold']:.0%})

- Sharpe: `{headline['sharpe_ungated']:.4f} -> {headline['sharpe_gated']:.4f}` (**{headline['sharpe_pct']:+.2f}%**)
- CVaR(95): `{headline['cvar_ungated']:.4f} -> {headline['cvar_gated']:.4f}` (**{headline['cvar_reduction_pct']:.2f}% tail-risk reduction**)
- Gate activity: `{headline['days_gated']}` low-exposure days

### Best full-sample profile (-2% bucket, soft @ 20%)

- Sharpe: `{best['sharpe_ungated']:.4f} -> {best['sharpe_gated']:.4f}` (**{best['sharpe_pct']:+.2f}%**)
- CVaR(95): `{best['cvar_ungated']:.4f} -> {best['cvar_gated']:.4f}` (**{best['cvar_reduction_pct']:.2f}% tail-risk reduction**)
{oot_line}
{END}"""


def update_readme(readme_path: Path, block: str) -> None:
    text = readme_path.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(block, text)
    else:
        text = text.replace("## Core Results\n", f"## Core Results\n\n{block}\n", 1)
    readme_path.write_text(text)


def main() -> None:
    config = load_config()
    block = build_metrics_block(config)
    update_readme(ROOT / "README.md", block)
    print(block)
    print("README.md updated.")


if __name__ == "__main__":
    main()
