"""Market structure features.

Features:
    - Credit spread proxy (HYG vs IEF)
    - Yield curve slope (10Y - 2Y)
    - Dollar index moves
"""

import numpy as np
import pandas as pd


def credit_spread_proxy(
    hyg_close: pd.Series, ief_close: pd.Series, window: int = 5
) -> pd.Series:
    """Compute credit spread proxy from HYG and IEF returns.

    When HYG (high yield bonds) underperforms IEF (treasuries),
    credit spreads are widening — a sign of market stress.

    Args:
        hyg_close: HYG ETF close prices.
        ief_close: IEF ETF close prices.
        window: Rolling window for return difference.

    Returns:
        Rolling return difference (HYG - IEF). Negative = stress.
    """
    hyg_ret = np.log(hyg_close / hyg_close.shift(1))
    ief_ret = np.log(ief_close / ief_close.shift(1))
    return (hyg_ret - ief_ret).rolling(window=window).sum()


def yield_curve_slope(treasury_2y: pd.Series, treasury_10y: pd.Series) -> pd.Series:
    """Compute yield curve slope (10Y - 2Y).

    Positive = normal curve. Negative = inverted (recession signal).

    Args:
        treasury_2y: 2-year treasury yield.
        treasury_10y: 10-year treasury yield.

    Returns:
        Yield curve slope in percentage points.
    """
    return treasury_10y - treasury_2y


def dollar_momentum(dxy_close: pd.Series, windows: list[int] = [5, 20]) -> pd.DataFrame:
    """Compute dollar index momentum.

    Sharp dollar moves often correlate with global risk-off.

    Args:
        dxy_close: Dollar index proxy (UUP ETF) close prices.
        windows: Momentum lookback windows.

    Returns:
        DataFrame with dollar momentum features.
    """
    result = pd.DataFrame(index=dxy_close.index)
    for w in windows:
        result[f"dxy_mom_{w}d"] = dxy_close.pct_change(w)
    return result


def build_market_structure_features(
    hyg_close: pd.Series,
    ief_close: pd.Series,
    treasury_2y: pd.Series,
    treasury_10y: pd.Series,
    dxy_close: pd.Series,
    credit_window: int = 5,
) -> pd.DataFrame:
    """Build all market structure features.

    Args:
        hyg_close: HYG ETF close prices.
        ief_close: IEF ETF close prices.
        treasury_2y: 2Y treasury yield series.
        treasury_10y: 10Y treasury yield series.
        dxy_close: Dollar index proxy close prices.
        credit_window: Window for credit spread computation.

    Returns:
        DataFrame with all market structure features.
    """
    features = pd.DataFrame()

    features["credit_spread"] = credit_spread_proxy(hyg_close, ief_close, credit_window)
    features["yield_curve"] = yield_curve_slope(treasury_2y, treasury_10y)

    dxy_mom = dollar_momentum(dxy_close)
    features = features.join(dxy_mom)

    return features
