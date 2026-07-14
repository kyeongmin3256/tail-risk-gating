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
    n_days = int(len(common))
    if primary_path.exists():
        primary = pd.read_csv(primary_path)
        bh_row = primary[primary["strategy"] == STRADDLE_BH_LABEL].iloc[0]
        gated_row = primary[primary["strategy"] != STRADDLE_BH_LABEL].iloc[0]
        days_gated = int(gated_row.get("days_skipped", days_gated))
        sharpe_u = float(bh_row["sharpe"])
        sharpe_g = float(gated_row["sharpe"])
        cvar_u = float(bh_row["cvar_5pct"])
        cvar_g = float(gated_row["cvar_5pct"])
        n_days = int(bh_row.get("n_days", n_days))

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
        "n_days": n_days,
    }


def build_metrics_block(config: dict) -> str:
    fwd = pd.read_csv(
        ROOT / "data/processed/target_continuous.csv",
        index_col="date",
        parse_dates=True,
    ).squeeze()

    best = summarize_threshold(2, fwd, config)

    oot_sharpe = None
    oot_cvar = None
    oot_path = ROOT / "data/model_outputs/significance_oot_t2_soft.csv"
    if oot_path.exists():
        oot = pd.read_csv(oot_path)
        best_oot = oot.loc[oot["gate_threshold"] == 0.2]
        if len(best_oot):
            row = best_oot.iloc[0]
            oot_sharpe = float(row["sharpe_diff"])
            oot_cvar = float(row["cvar_improvement"])

    oot_section = ""
    if oot_sharpe is not None and oot_cvar is not None:
        oot_section = f"""
### Out-of-sample check — soft gate (-2% @ 20%, last 756 days)

| Diagnostic | Value |
|------------|-------|
| Sharpe delta (gated − ungated) | **{oot_sharpe:+.2f}** |
| CVaR improvement | **{oot_cvar:+.3f}** |
"""

    return f"""{START}
### Best full-sample profile — soft gate (-2% @ 20%) vs Short Straddle B&H

Walk-forward evaluation on the short ATM SPY straddle proxy (~{best['n_days']:,} days).

| Metric | Ungated (B&H) | Gated | Change |
|--------|---------------|-------|--------|
| Sharpe | {best['sharpe_ungated']:.2f} | **{best['sharpe_gated']:.2f}** | **{best['sharpe_pct']:+.1f}%** |
| CVaR (95%) | {best['cvar_ungated']*100:.2f}% | **{best['cvar_gated']*100:.2f}%** | **{best['cvar_reduction_pct']:.0f}%** tail-risk reduction |
{oot_section}
### Headline vs deeper buckets

Deeper loss buckets (-4% and below) use a **hard** gate @ 15%. They are useful stress labels for the dashboard, but the **resume / portfolio headline** is the **-2% soft @ 20%** profile above (best risk-adjusted gated-vs-ungated tradeoff in current artifacts).

Artifacts: `outputs/threshold_-2/gating_primary.csv`, `data/model_outputs/significance_oot_t2_soft.csv`, `data/model_outputs/significance_sweep_t2_soft.csv`
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
