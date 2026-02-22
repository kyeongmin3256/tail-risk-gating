"""Volatility-related features.

Features:
    - Realized volatility (multiple windows)
    - IV-RV spread (VIX minus realized vol)
    - VIX level
    - VVIX (vol of vol)
    - SKEW index
    - VIX term structure slope and inversion flag
"""

import numpy as np
import pandas as pd


def realized_volatility(
    spy_close: pd.Series, windows: list[int] = [5, 10, 20]
) -> pd.DataFrame:
    """Compute annualized realized volatility over rolling windows.

    Args:
        spy_close: SPY daily close prices.
        windows: List of lookback windows in trading days.

    Returns:
        DataFrame with columns like 'rvol_5d', 'rvol_10d', etc.
    """
    log_returns = np.log(spy_close / spy_close.shift(1))

    result = pd.DataFrame(index=spy_close.index)
    for w in windows:
        result[f"rvol_{w}d"] = log_returns.rolling(window=w).std() * np.sqrt(252)

    return result


def iv_rv_spread(vix: pd.Series, rvol_20d: pd.Series) -> pd.Series:
    """Compute implied volatility minus realized volatility spread.

    When this spread is abnormally high, options sellers are collecting
    more premium relative to actual risk — but extreme readings in
    either direction can signal danger.

    Args:
        vix: VIX index values (annualized implied vol in %).
        rvol_20d: 20-day realized vol (annualized, as decimal).

    Returns:
        Series of IV-RV spread values.
    """
    # VIX is in percentage points (e.g., 20 = 20%), rvol is decimal (e.g., 0.20)
    vix_aligned, rvol_aligned = vix.align(rvol_20d, join="inner")
    return vix_aligned - (rvol_aligned * 100)


def vix_term_structure(
    vix: pd.Series, vix3m: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Compute VIX term structure slope and inversion flag.

    Normal: VIX3M > VIX (upward sloping, contango)
    Inverted: VIX > VIX3M (backwardation — signals acute stress)

    Args:
        vix: VIX index (spot/front-month implied vol).
        vix3m: VIX3M index (3-month implied vol).

    Returns:
        Tuple of (slope, inversion_flag).
        slope: (VIX3M - VIX) / VIX — positive = normal, negative = inverted
        inversion_flag: 1 if inverted, 0 otherwise
    """
    vix_aligned, vix3m_aligned = vix.align(vix3m, join="inner")
    slope = (vix3m_aligned - vix_aligned) / vix_aligned
    inversion = (vix_aligned > vix3m_aligned).astype(int)
    return slope, inversion


def build_volatility_features(
    spy_close: pd.Series,
    vix: pd.Series,
    vvix: pd.Series,
    skew: pd.Series,
    vix3m: pd.Series,
    vix9d: pd.Series | None = None,
    rvol_windows: list[int] = [5, 10, 20],
) -> pd.DataFrame:
    """Build all volatility features into a single DataFrame.

    Args:
        spy_close: SPY close prices.
        vix: VIX index.
        vvix: VVIX index.
        skew: SKEW index.
        vix3m: VIX3M index.
        vix9d: VIX9D index (optional, shorter history).
        rvol_windows: Windows for realized vol computation.

    Returns:
        DataFrame with all volatility features, aligned on date index.
    """
    features = pd.DataFrame(index=spy_close.index)

    # Realized vol
    rvol = realized_volatility(spy_close, rvol_windows)
    features = features.join(rvol)

    # Raw levels
    features["vix"] = vix
    features["vvix"] = vvix
    features["skew"] = skew

    # IV-RV spread
    if "rvol_20d" in features.columns:
        features["iv_rv_spread"] = iv_rv_spread(vix, features["rvol_20d"])

    # Term structure
    slope, inversion = vix_term_structure(vix, vix3m)
    features["vix_term_slope"] = slope
    features["vix_term_inverted"] = inversion

    # Short-term vs spot VIX (if available)
    if vix9d is not None:
        features["vix9d_vix_ratio"] = vix9d / vix

    return features
