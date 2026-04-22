"""Momentum and price behavior features.

Features:
    - SPY returns (multiple windows)
    - Distance from moving average
    - Volume ratio
    - Rolling max drawdown
    - Consecutive down days
    - Largest single-day move
"""

import pandas as pd


def spy_returns(spy_close: pd.Series, windows: list[int] = [1, 5, 10, 20]) -> pd.DataFrame:
    """Compute SPY returns over multiple horizons.

    Args:
        spy_close: SPY close prices.
        windows: Lookback windows in trading days.

    Returns:
        DataFrame with return columns.
    """
    result = pd.DataFrame(index=spy_close.index)
    for w in windows:
        result[f"spy_ret_{w}d"] = spy_close.pct_change(w)
    return result


def distance_from_ma(spy_close: pd.Series, ma_window: int = 50) -> pd.Series:
    """Compute distance of price from moving average.

    How far the market has stretched from its trend.
    Extreme readings (either direction) can precede reversals.

    Args:
        spy_close: SPY close prices.
        ma_window: Moving average period.

    Returns:
        (price - MA) / MA as a decimal.
    """
    ma = spy_close.rolling(window=ma_window).mean()
    return (spy_close - ma) / ma


def volume_ratio(spy_volume: pd.Series, ma_window: int = 20) -> pd.Series:
    """Compute volume relative to recent average.

    Unusual volume spikes often precede large moves.

    Args:
        spy_volume: SPY daily volume.
        ma_window: Baseline average window.

    Returns:
        Today's volume / average volume ratio.
    """
    avg_volume = spy_volume.rolling(window=ma_window).mean()
    return spy_volume / avg_volume


def rolling_max_drawdown(spy_close: pd.Series, window: int = 5) -> pd.Series:
    """Compute worst peak-to-trough drawdown in trailing window.

    Args:
        spy_close: SPY close prices.
        window: Lookback window.

    Returns:
        Maximum drawdown (negative value) over trailing window.
    """
    rolling_max = spy_close.rolling(window=window).max()
    drawdown = (spy_close - rolling_max) / rolling_max
    return drawdown


def consecutive_down_days(spy_close: pd.Series) -> pd.Series:
    """Count consecutive negative return days.

    Streaks of losses can precede further selling or capitulation.

    Args:
        spy_close: SPY close prices.

    Returns:
        Count of consecutive down days (0 if today was up).
    """
    daily_ret = spy_close.pct_change()
    is_down = (daily_ret < 0).astype(int)

    # Count consecutive 1s
    result = pd.Series(0, index=spy_close.index, dtype=int)
    for i in range(1, len(result)):
        if is_down.iloc[i] == 1:
            result.iloc[i] = result.iloc[i - 1] + 1
        else:
            result.iloc[i] = 0

    return result


def max_single_day_move(spy_close: pd.Series, window: int = 20) -> pd.Series:
    """Largest absolute single-day return in trailing window.

    Captures recent "jumpiness" — large moves tend to cluster.

    Args:
        spy_close: SPY close prices.
        window: Lookback window.

    Returns:
        Max absolute daily return over trailing window.
    """
    daily_ret = spy_close.pct_change().abs()
    return daily_ret.rolling(window=window).max()


def build_momentum_features(
    spy_close: pd.Series,
    spy_volume: pd.Series,
    ret_windows: list[int] = [1, 5, 10, 20],
    ma_window: int = 50,
    volume_ma_window: int = 20,
    drawdown_window: int = 5,
) -> pd.DataFrame:
    """Build all momentum and price behavior features.

    Args:
        spy_close: SPY close prices.
        spy_volume: SPY daily volume.
        ret_windows: Return lookback windows.
        ma_window: Moving average window.
        volume_ma_window: Volume average window.
        drawdown_window: Drawdown lookback window.

    Returns:
        DataFrame with all momentum features.
    """
    features = pd.DataFrame(index=spy_close.index)

    # Returns
    rets = spy_returns(spy_close, ret_windows)
    features = features.join(rets)

    # Distance from MA
    features["dist_from_ma"] = distance_from_ma(spy_close, ma_window)

    # Volume
    features["volume_ratio"] = volume_ratio(spy_volume, volume_ma_window)

    # Drawdown
    features["max_drawdown_5d"] = rolling_max_drawdown(spy_close, drawdown_window)

    # Consecutive downs
    features["consec_down_days"] = consecutive_down_days(spy_close)

    # Max single day move
    features["max_move_20d"] = max_single_day_move(spy_close, 20)

    return features
