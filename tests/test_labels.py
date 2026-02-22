"""Tests for strategy label computation."""

import numpy as np
import pandas as pd
import pytest

from src.labels.strategy import compute_forward_returns, compute_labels


@pytest.fixture
def known_prices():
    """Prices with a known crash event."""
    dates = pd.bdate_range("2020-01-01", periods=20)
    # Stable, then crash on day 10-11
    prices = [100] * 10 + [85, 80, 78, 82, 85, 88, 90, 92, 94, 96]
    return pd.Series(prices, index=dates, dtype=float)


@pytest.fixture
def flat_vix():
    """Constant VIX for simple testing."""
    dates = pd.bdate_range("2020-01-01", periods=20)
    return pd.Series([20.0] * 20, index=dates)


class TestForwardReturns:
    def test_basic(self):
        prices = pd.Series([100.0, 110.0, 105.0, 120.0])
        result = compute_forward_returns(prices, horizon=1)
        assert result.iloc[0] == pytest.approx(0.10)  # 100 → 110
        assert result.iloc[1] == pytest.approx(-0.04545, rel=1e-3)  # 110 → 105

    def test_last_rows_are_nan(self):
        prices = pd.Series([100.0, 110.0, 105.0, 120.0])
        result = compute_forward_returns(prices, horizon=2)
        assert pd.isna(result.iloc[-1])
        assert pd.isna(result.iloc[-2])

    def test_uses_future_data(self):
        """Forward returns SHOULD use future data (it's the target)."""
        prices = pd.Series([100.0, 110.0, 105.0])
        result = compute_forward_returns(prices, horizon=1)
        # Value at index 0 uses price at index 1
        assert result.iloc[0] == pytest.approx(0.10)


class TestLabels:
    def test_crash_detected(self, known_prices, flat_vix):
        """Labels should flag the crash period."""
        labels, _ = compute_labels(
            known_prices, flat_vix, horizon=5, threshold=-0.10, method="realized_move"
        )
        # Days 5-9 should see the upcoming crash (>10% move in next 5 days)
        # Day 5: forward 5d prices go from 100 to 85 = -15% → flagged
        assert labels.iloc[5] == 1

    def test_calm_period_not_flagged(self, known_prices, flat_vix):
        """Calm periods should not be flagged."""
        labels, _ = compute_labels(
            known_prices, flat_vix, horizon=5, threshold=-0.10, method="realized_move"
        )
        # First few days: prices are flat → no flag
        assert labels.iloc[0] == 0

    def test_label_counts_reasonable(self):
        """With random data, very few days should exceed -15% in 5 days."""
        dates = pd.bdate_range("2010-01-01", periods=2000)
        np.random.seed(42)
        returns = np.random.normal(0.0003, 0.01, 2000)
        prices = pd.Series(100 * np.exp(np.cumsum(returns)), index=dates)
        vix = pd.Series([15.0] * 2000, index=dates)

        labels, _ = compute_labels(
            prices, vix, horizon=5, threshold=-0.15, method="realized_move"
        )
        # With 1% daily vol, -15% in 5 days is very rare
        pct_positive = labels.sum() / labels.notna().sum()
        assert pct_positive < 0.05  # Less than 5% of days
