"""Walk-forward backtesting for time-series models.

Implements expanding-window walk-forward validation:
    1. Train on data up to time T
    2. Predict on T+1 to T+retrain_freq
    3. Expand training window, retrain, repeat

This prevents look-ahead bias that standard cross-validation
would introduce on time-series data.

Usage:
    from src.models.walk_forward import WalkForwardEngine
    engine = WalkForwardEngine(config)
    results = engine.run(features, labels)
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.models.trainer import TailRiskModel

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardResult:
    """Container for walk-forward backtest results."""

    predictions: pd.Series = field(default_factory=pd.Series)
    actuals: pd.Series = field(default_factory=pd.Series)
    fold_stats: list[dict] = field(default_factory=list)
    models: list[TailRiskModel] = field(default_factory=list)

    @property
    def n_folds(self) -> int:
        return len(self.fold_stats)


class WalkForwardEngine:
    """Expanding-window walk-forward backtesting engine."""

    def __init__(self, config: dict):
        """Initialize with project config.

        Args:
            config: Project configuration dictionary.
        """
        self.config = config
        wf_config = config["model"]["walk_forward"]
        self.retrain_freq = wf_config["retrain_frequency"]
        self.min_train_size = wf_config["min_train_size"]
        self.seed = config["model"]["seed"]

    def run(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> WalkForwardResult:
        """Execute walk-forward backtest.

        Uses expanding window: each fold trains on all data up to
        the split point, then predicts the next retrain_freq rows.

        Args:
            features: Feature DataFrame sorted by date.
            labels: Binary label Series aligned with features.

        Returns:
            WalkForwardResult with out-of-sample predictions.
        """
        result = WalkForwardResult()
        all_preds = {}
        all_actuals = {}
        n_rows = len(features)

        # Generate fold boundaries
        fold_starts = list(range(self.min_train_size, n_rows, self.retrain_freq))

        logger.info(
            f"Walk-forward: {len(fold_starts)} folds, "
            f"retrain every {self.retrain_freq} days, "
            f"min train size {self.min_train_size}"
        )

        for fold_idx, split_idx in enumerate(fold_starts):
            # Training: everything before split_idx
            X_train = features.iloc[:split_idx]
            y_train = labels.iloc[:split_idx]

            # Test: next retrain_freq rows (or remaining)
            test_end = min(split_idx + self.retrain_freq, n_rows)
            X_test = features.iloc[split_idx:test_end]
            y_test = labels.iloc[split_idx:test_end]

            if len(X_test) == 0:
                break

            # Use last 20% of training as validation for early stopping
            val_size = max(int(len(X_train) * 0.2), 100)
            X_tr = X_train.iloc[:-val_size]
            y_tr = y_train.iloc[:-val_size]
            X_val = X_train.iloc[-val_size:]
            y_val = y_train.iloc[-val_size:]

            # Train
            model = TailRiskModel(self.config)
            model.fit(X_tr, y_tr, X_val, y_val)

            # Predict
            probas = model.predict_proba(X_test)

            # Store results
            for date, prob in zip(X_test.index, probas):
                all_preds[date] = prob
            for date, label in zip(y_test.index, y_test.values):
                all_actuals[date] = label

            fold_stat = {
                "fold": fold_idx,
                "train_size": len(X_tr),
                "val_size": val_size,
                "test_size": len(X_test),
                "train_start": X_tr.index[0],
                "train_end": X_tr.index[-1],
                "test_start": X_test.index[0],
                "test_end": X_test.index[-1],
                "pos_rate_train": y_tr.mean(),
                "pos_rate_test": y_test.mean(),
                "mean_pred": probas.mean(),
            }
            result.fold_stats.append(fold_stat)
            result.models.append(model)

            if fold_idx % 5 == 0:
                logger.info(
                    f"  Fold {fold_idx}: train {len(X_tr)}, "
                    f"test {len(X_test)}, "
                    f"test pos rate {y_test.mean():.3f}, "
                    f"mean pred {probas.mean():.3f}"
                )

        result.predictions = pd.Series(all_preds, name="predicted_prob").sort_index()
        result.actuals = pd.Series(all_actuals, name="actual").sort_index()

        logger.info(
            f"Walk-forward complete: {result.n_folds} folds, "
            f"{len(result.predictions)} out-of-sample predictions"
        )

        return result
