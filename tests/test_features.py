"""Tests for feature pipeline correctness and no-leakage guarantees.

These tests verify:
    1. Features are computed correctly on known inputs
    2. No feature uses future data (the most critical test)
    3. Feature matrix has expected shape and no unexpected NaNs
"""

import numpy as np
import pandas as pd
import pytest

from src.features.volatility import realized_volatility, iv_rv_spread, vix_term_structure
from src.features.momentum import (
    spy_returns,
    consecutive_down_days,
    volume_ratio,
    distance_from_ma,
)
from src.features.calendar import earnings_season_flag


# --- Fixtures ---

@pytest.fixture
def sample_prices():
    """Create a simple price series for testing."""
    dates = pd.bdate_range("2020-01-01", periods=60)
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.01, 60)
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def sample_volume():
    """Create a simple volume series for testing."""
    dates = pd.bdate_range("2020-01-01", periods=60)
    np.random.seed(42)
    volume = np.random.randint(50_000_000, 150_000_000, 60)
    return pd.Series(volume, index=dates, name="Volume")


# --- Feature Correctness Tests ---

class TestRealizedVolatility:
    def test_output_shape(self, sample_prices):
        result = realized_volatility(sample_prices, windows=[5, 10])
        assert result.shape == (60, 2)
        assert "rvol_5d" in result.columns
        assert "rvol_10d" in result.columns

    def test_first_rows_are_nan(self, sample_prices):
        result = realized_volatility(sample_prices, windows=[5])
        # First 5 rows should be NaN (need 5 returns, first return is NaN)
        assert result["rvol_5d"].iloc[:5].isna().all()

    def test_values_are_positive(self, sample_prices):
        result = realized_volatility(sample_prices, windows=[5])
        valid = result["rvol_5d"].dropna()
        assert (valid > 0).all()

    def test_annualized(self, sample_prices):
        """Realized vol should be annualized (roughly 10-30% for typical stocks)."""
        result = realized_volatility(sample_prices, windows=[20])
        valid = result["rvol_20d"].dropna()
        # With seed=42 and 1% daily vol, annualized should be ~15-20%
        assert valid.mean() > 0.05  # At least 5% annualized
        assert valid.mean() < 0.50  # Less than 50% annualized


class TestIVRVSpread:
    def test_basic_computation(self):
        vix = pd.Series([20.0, 25.0, 15.0])
        rvol = pd.Series([0.15, 0.20, 0.18])
        result = iv_rv_spread(vix, rvol)
        expected = pd.Series([5.0, 5.0, -3.0])
        pd.testing.assert_series_equal(result, expected)


class TestVIXTermStructure:
    def test_normal_contango(self):
        vix = pd.Series([15.0])
        vix3m = pd.Series([18.0])
        slope, inversion = vix_term_structure(vix, vix3m)
        assert slope.iloc[0] > 0  # Positive slope = normal
        assert inversion.iloc[0] == 0  # Not inverted

    def test_backwardation(self):
        vix = pd.Series([30.0])
        vix3m = pd.Series([22.0])
        slope, inversion = vix_term_structure(vix, vix3m)
        assert slope.iloc[0] < 0  # Negative slope = inverted
        assert inversion.iloc[0] == 1  # Inverted


class TestMomentumFeatures:
    def test_returns_shape(self, sample_prices):
        result = spy_returns(sample_prices, windows=[1, 5])
        assert result.shape[1] == 2

    def test_consecutive_down_days(self):
        prices = pd.Series([100, 99, 98, 97, 100, 99])
        result = consecutive_down_days(prices)
        # Day 0: undefined (no prev), Day 1: down(1), Day 2: down(2),
        # Day 3: down(3), Day 4: up(0), Day 5: down(1)
        assert result.iloc[3] == 3
        assert result.iloc[4] == 0
        assert result.iloc[5] == 1

    def test_volume_ratio(self, sample_volume):
        result = volume_ratio(sample_volume, ma_window=20)
        # After warmup, ratio should be around 1.0 on average
        valid = result.dropna()
        assert 0.5 < valid.mean() < 1.5


class TestCalendarFeatures:
    def test_earnings_season(self):
        # Jan 15 should be earnings season
        dates = pd.DatetimeIndex(["2020-01-15", "2020-02-15", "2020-04-20"])
        result = earnings_season_flag(dates)
        assert result[0] == 1  # Jan 15 = earnings season
        assert result[1] == 0  # Feb 15 = not earnings season
        assert result[2] == 1  # Apr 20 = earnings season


# --- No-Leakage Tests (MOST IMPORTANT) ---

class TestNoLeakage:
    """Verify that no feature uses future data.

    Strategy: Truncate the price series at different points and verify
    that features computed up to that point don't change when more
    future data is added.
    """

    def test_realized_vol_no_leakage(self, sample_prices):
        """Features at time t should not change if we add data after t."""
        # Compute with full data
        full = realized_volatility(sample_prices, windows=[5])

        # Compute with truncated data (first 40 rows only)
        truncated = realized_volatility(sample_prices.iloc[:40], windows=[5])

        # Features at row 39 should be identical
        pd.testing.assert_series_equal(
            full.iloc[39],
            truncated.iloc[39],
            check_names=False,
        )

    def test_returns_no_leakage(self, sample_prices):
        full = spy_returns(sample_prices, windows=[5])
        truncated = spy_returns(sample_prices.iloc[:40], windows=[5])
        pd.testing.assert_series_equal(
            full.iloc[39],
            truncated.iloc[39],
            check_names=False,
        )

    def test_distance_from_ma_no_leakage(self, sample_prices):
        full = distance_from_ma(sample_prices, ma_window=20)
        truncated = distance_from_ma(sample_prices.iloc[:40], ma_window=20)
        assert full.iloc[39] == truncated.iloc[39]
