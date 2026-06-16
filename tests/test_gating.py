"""Tests for trade-gating exposure scaling."""

import numpy as np
import pandas as pd

from src.evaluation.gating import (
    STRADDLE_BH_LABEL,
    apply_gating,
    gating_config_for,
    soft_exposure_scale,
)


def test_soft_scale_at_threshold_is_one():
    scale = soft_exposure_scale(np.array([0.20]), 0.20)
    assert scale[0] == 1.0


def test_soft_scale_at_one_is_zero():
    scale = soft_exposure_scale(np.array([1.0]), 0.20)
    assert scale[0] == 0.0


def test_hard_gate_zeros_high_risk_days():
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    returns = pd.Series([0.01, 0.02, -0.05], index=idx)
    probs = pd.Series([0.10, 0.90, 0.15], index=idx)
    gated = apply_gating(returns, probs, gate_threshold=0.20, mode="hard")
    assert gated.iloc[0] == 0.01
    assert gated.iloc[1] == 0.0
    assert gated.iloc[2] == -0.05


def test_threshold_two_defaults_to_soft_gate():
    cfg = gating_config_for(2)
    assert cfg["mode"] == "soft"
    assert cfg["gate_threshold"] == 0.20


def test_straddle_label_constant():
    assert "Straddle" in STRADDLE_BH_LABEL
