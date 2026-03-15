"""Backtesting: gated vs ungated short-volatility strategy.

Compares performance when the model gates (skips) high-risk days
versus always trading. Key metrics:
    - Max drawdown reduction
    - CVaR improvement
    - Premium sacrificed (cost of sitting out)

Usage:
    from src.evaluation.backtest import StrategyBacktest
    bt = StrategyBacktest(config)
    results = bt.run(predictions, actuals, forward_returns)
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class StrategyBacktest:
    """Compare gated vs ungated short-vol strategy performance."""

    def __init__(self, config: dict):
        """Initialize with project config.

        Args:
            config: Project configuration dictionary.
        """
        self.config = config

    def run(
        self,
        predictions: pd.Series,
        actuals: pd.Series,
        forward_returns: pd.Series,
        gate_thresholds: list[float] | None = None,
    ) -> pd.DataFrame:
        """Run gated vs ungated comparison at various thresholds.

        The "gate" means: if predicted P(tail) > threshold, skip that day.

        Args:
            predictions: Predicted tail risk probabilities.
            actuals: True binary labels.
            forward_returns: Actual forward returns (continuous).
            gate_thresholds: List of probability thresholds to test.
                Defaults to [0.05, 0.10, 0.15, 0.20, 0.30, 0.50].

        Returns:
            DataFrame comparing strategy performance at each threshold.
        """
        if gate_thresholds is None:
            gate_thresholds = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]

        # Align all series
        common_idx = predictions.index.intersection(
            actuals.index
        ).intersection(forward_returns.index)

        preds = predictions.loc[common_idx]
        acts = actuals.loc[common_idx]
        fwd = forward_returns.loc[common_idx]

        # Ungated baseline
        baseline = self._compute_stats(fwd, "ungated (always trade)")

        results = [baseline]
        for threshold in gate_thresholds:
            # Gate: skip days where predicted risk > threshold
            trade_mask = preds <= threshold
            gated_returns = fwd[trade_mask]

            stats = self._compute_stats(
                gated_returns,
                f"gate @ {threshold:.0%}",
            )
            stats["gate_threshold"] = threshold
            stats["days_traded"] = int(trade_mask.sum())
            stats["days_skipped"] = int((~trade_mask).sum())
            stats["pct_traded"] = trade_mask.mean()
            stats["tail_events_avoided"] = int(acts[~trade_mask].sum())
            stats["tail_events_total"] = int(acts.sum())

            results.append(stats)

        df = pd.DataFrame(results)
        logger.info(f"Backtest complete across {len(gate_thresholds)} thresholds")
        return df

    def _compute_stats(self, returns: pd.Series, label: str) -> dict:
        """Compute strategy performance statistics.

        Args:
            returns: Series of period returns.
            label: Strategy label for display.

        Returns:
            Dictionary of performance metrics.
        """
        returns = returns.dropna()

        if len(returns) == 0:
            return {"strategy": label}

        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max

        return {
            "strategy": label,
            "total_return": float(cumulative.iloc[-1] - 1),
            "mean_daily_return": float(returns.mean()),
            "volatility": float(returns.std() * np.sqrt(252)),
            "sharpe": float(
                returns.mean() / returns.std() * np.sqrt(252)
                if returns.std() > 0
                else 0
            ),
            "max_drawdown": float(drawdown.min()),
            "cvar_5pct": float(returns.quantile(0.05)),
            "worst_day": float(returns.min()),
            "n_days": len(returns),
        }


def format_backtest_report(results: pd.DataFrame) -> str:
    """Format backtest results as a readable report.

    Args:
        results: DataFrame from StrategyBacktest.run().

    Returns:
        Formatted multi-line string.
    """
    lines = [
        "=" * 70,
        "GATED vs UNGATED STRATEGY COMPARISON",
        "=" * 70,
    ]

    for _, row in results.iterrows():
        lines.append(f"\n--- {row['strategy']} ---")
        lines.append(f"  Days traded:     {row.get('n_days', 'N/A')}")
        lines.append(f"  Total return:    {row.get('total_return', 0):.2%}")
        lines.append(f"  Sharpe:          {row.get('sharpe', 0):.2f}")
        lines.append(f"  Max drawdown:    {row.get('max_drawdown', 0):.2%}")
        lines.append(f"  CVaR (5%):       {row.get('cvar_5pct', 0):.2%}")

        if "days_skipped" in row and pd.notna(row.get("days_skipped")):
            lines.append(f"  Days skipped:    {int(row['days_skipped'])}")
            lines.append(
                f"  Tail events avoided: "
                f"{int(row.get('tail_events_avoided', 0))}"
                f"/{int(row.get('tail_events_total', 0))}"
            )

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)
