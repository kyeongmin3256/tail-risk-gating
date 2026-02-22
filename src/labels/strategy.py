"""Strategy definition and label computation.

Defines the canonical strategy (short ATM straddle on SPY) and
computes binary labels for whether the strategy's loss exceeds
a given threshold over a given horizon.

CRITICAL DESIGN DECISIONS:
    1. We use a PROXY for short straddle P&L since we don't have
       real options chain data. The proxy is based on realized vs
       implied volatility — the core driver of short vol P&L.
    2. Labels use FORWARD-LOOKING returns (this is the target,
       not a feature). Features must be strictly backward-looking.
    3. The last `horizon` rows cannot have labels (no future data).

Strategy Proxy:
    Short straddle P&L ≈ premium_collected - |realized_move|
    Where:
        premium_collected ∝ implied_vol (VIX as proxy)
        realized_move = SPY return over next N days

    Simplified loss metric:
        loss = -(|SPY_return_next_N_days| - VIX_daily_scaled * sqrt(N))
    If loss < -threshold → label = 1 (bad outcome, should not have traded)
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_forward_returns(
    spy_close: pd.Series, horizon: int = 5
) -> pd.Series:
    """Compute forward SPY returns over the given horizon.

    IMPORTANT: This is the TARGET variable, computed using future data.
    It must NEVER be used as a feature.

    Args:
        spy_close: SPY close prices.
        horizon: Forward-looking window in trading days.

    Returns:
        Series of forward returns. Last `horizon` rows will be NaN.
    """
    return spy_close.shift(-horizon) / spy_close - 1


def compute_strategy_loss(
    spy_close: pd.Series,
    vix: pd.Series,
    horizon: int = 5,
) -> pd.Series:
    """Compute proxy P&L for a short ATM straddle on SPY.

    The short straddle seller:
        - Collects premium proportional to implied vol (VIX)
        - Loses when |realized move| > premium collected

    Proxy formula:
        premium_proxy = VIX / 100 / sqrt(252) * sqrt(horizon)
        realized_loss = |forward_return_over_horizon|
        strategy_pnl = premium_proxy - realized_loss

    Negative strategy_pnl = the trade lost money.

    Args:
        spy_close: SPY close prices.
        vix: VIX index values.
        horizon: Holding period in trading days.

    Returns:
        Series of strategy P&L (negative = loss).
        Last `horizon` rows will be NaN.
    """
    forward_ret = compute_forward_returns(spy_close, horizon)

    # Premium collected (annualized VIX → daily → scale to horizon)
    # VIX is annualized vol in percentage points
    daily_vol = vix / 100 / np.sqrt(252)
    premium_proxy = daily_vol * np.sqrt(horizon)

    # Short straddle loses based on absolute move minus premium
    # Straddle has exposure to moves in BOTH directions
    strategy_pnl = premium_proxy - forward_ret.abs()

    return strategy_pnl


def compute_labels(
    spy_close: pd.Series,
    vix: pd.Series,
    horizon: int = 5,
    threshold: float = -0.15,
    method: str = "realized_move",
) -> tuple[pd.Series, pd.Series]:
    """Compute binary labels for tail risk events.

    Two methods available:
        1. "realized_move": Simply whether |SPY move| over horizon
           exceeds threshold. Simpler and more robust.
        2. "strategy_pnl": Whether the short straddle proxy P&L
           is worse than threshold. More realistic but noisier.

    Args:
        spy_close: SPY close prices.
        vix: VIX index values.
        horizon: Forward-looking window in trading days.
        threshold: Loss threshold (negative number, e.g., -0.15 for -15%).
        method: "realized_move" or "strategy_pnl".

    Returns:
        Tuple of (labels, continuous_target).
        labels: Binary series (1 = loss exceeded threshold, 0 = safe).
        continuous_target: The underlying continuous loss metric.
    """
    if method == "realized_move":
        # Simple: did SPY move more than threshold in either direction?
        forward_ret = compute_forward_returns(spy_close, horizon)
        continuous_target = forward_ret
        # For short straddle, loss comes from moves in EITHER direction
        labels = (forward_ret.abs() > abs(threshold)).astype(int)

    elif method == "strategy_pnl":
        # More realistic: short straddle proxy P&L
        strategy_pnl = compute_strategy_loss(spy_close, vix, horizon)
        continuous_target = strategy_pnl
        labels = (strategy_pnl < threshold).astype(int)

    else:
        raise ValueError(f"Unknown method: {method}. Use 'realized_move' or 'strategy_pnl'.")

    n_positive = labels.sum()
    n_total = labels.notna().sum()
    pct = n_positive / n_total * 100 if n_total > 0 else 0

    logger.info(
        f"Labels computed (method={method}, horizon={horizon}, threshold={threshold}):"
    )
    logger.info(f"  {n_positive}/{n_total} positive labels ({pct:.1f}%)")

    return labels, continuous_target
