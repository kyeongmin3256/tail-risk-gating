"""Shared trade-gating logic for backtests, significance tests, and dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd

STRADDLE_BH_LABEL = "Short Straddle B&H"

# OOT-tuned defaults: soft gate for -2%, hard gate for deeper buckets.
DEFAULT_GATING_BY_THRESHOLD: dict[int, dict[str, str | float]] = {
    2: {"mode": "soft", "gate_threshold": 0.20},
    4: {"mode": "hard", "gate_threshold": 0.15},
    6: {"mode": "hard", "gate_threshold": 0.15},
    8: {"mode": "hard", "gate_threshold": 0.15},
}


def gating_config_for(threshold_pct: int, config: dict | None = None) -> dict[str, str | float]:
    """Return gating mode and threshold for a loss-tolerance bucket."""
    if config and "gating" in config:
        by_thr = config["gating"].get("by_threshold", {})
        key = str(abs(threshold_pct))
        if key in by_thr:
            row = by_thr[key]
            return {
                "mode": row.get("mode", "hard"),
                "gate_threshold": float(row["gate_threshold"]),
            }
    return DEFAULT_GATING_BY_THRESHOLD.get(
        abs(threshold_pct),
        {"mode": "hard", "gate_threshold": 0.15},
    )


def soft_exposure_scale(probabilities: np.ndarray, gate_threshold: float) -> np.ndarray:
    """Scale exposure from 1.0 at gate_threshold down to 0.0 at probability 1.0."""
    p = np.asarray(probabilities, dtype=float)
    denom = max(1e-8, 1.0 - gate_threshold)
    return 1.0 - np.clip((p - gate_threshold) / denom, 0.0, 1.0)


def exposure_scale(
    probabilities: pd.Series | np.ndarray,
    gate_threshold: float,
    mode: str,
) -> np.ndarray:
    """Return per-day exposure multiplier in [0, 1]."""
    p = np.asarray(probabilities, dtype=float)
    if mode == "hard":
        return (p <= gate_threshold).astype(float)
    if mode == "soft":
        return soft_exposure_scale(p, gate_threshold)
    raise ValueError(f"Unknown gating mode: {mode}")


def apply_gating(
    returns: pd.Series,
    probabilities: pd.Series,
    gate_threshold: float,
    mode: str,
) -> pd.Series:
    """Apply hard or soft gating to short-straddle proxy returns."""
    common = returns.index.intersection(probabilities.index)
    r = returns.loc[common].astype(float)
    p = probabilities.loc[common].astype(float)
    scale = exposure_scale(p, gate_threshold, mode)
    return pd.Series(r.values * scale, index=common, name=returns.name)


def gated_strategy_label(mode: str, gate_threshold: float) -> str:
    mode_label = "Soft" if mode == "soft" else "Hard"
    return f"{mode_label} Gate @ {gate_threshold:.0%}"
