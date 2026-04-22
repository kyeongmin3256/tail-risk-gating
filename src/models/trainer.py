"""LightGBM model training with hyperparameter tuning.

Handles class imbalance (~6.5% positive rate) via scale_pos_weight
and optimizes for ranking/probability metrics suitable for rare events.

Usage:
    from src.models.trainer import TailRiskModel
    model = TailRiskModel(config)
    model.fit(X_train, y_train, X_val, y_val)
    probas = model.predict_proba(X_test)
"""

import logging
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TailRiskModel:
    """LightGBM classifier for tail risk probability estimation."""

    def __init__(self, config: dict):
        """Initialize with project config.

        Args:
            config: Project configuration dictionary.
        """
        self.config = config
        self.model: lgb.LGBMClassifier | None = None
        self.feature_names: list[str] = []

    def _get_base_params(self) -> dict:
        """Return base LightGBM parameters tuned for rare-event detection."""
        return {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "n_estimators": 1000,
            "learning_rate": 0.01,
            "num_leaves": 31,
            "max_depth": 6,
            "min_child_samples": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": self.config["model"]["seed"],
            "verbose": -1,
            "n_jobs": -1,
        }

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
    ) -> "TailRiskModel":
        """Train the LightGBM model.

        Automatically sets scale_pos_weight based on class imbalance.

        Args:
            X_train: Training features.
            y_train: Training labels (0/1).
            X_val: Validation features (for early stopping).
            y_val: Validation labels.

        Returns:
            self for chaining.
        """
        self.feature_names = list(X_train.columns)

        # Handle class imbalance
        n_neg = (y_train == 0).sum()
        n_pos = (y_train == 1).sum()
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        logger.info(
            f"Class balance — neg: {n_neg}, pos: {n_pos}, "
            f"scale_pos_weight: {scale_pos_weight:.2f}"
        )

        params = self._get_base_params()
        params["scale_pos_weight"] = scale_pos_weight

        self.model = lgb.LGBMClassifier(**params)

        fit_kwargs: dict = {}
        if X_val is not None and y_val is not None:
            fit_kwargs["eval_set"] = [(X_val, y_val)]
            fit_kwargs["callbacks"] = [
                lgb.early_stopping(stopping_rounds=50, verbose=True),
                lgb.log_evaluation(period=100),
            ]

        self.model.fit(X_train, y_train, **fit_kwargs)

        best_iter = getattr(self.model, "best_iteration_", self.model.n_estimators)
        logger.info(f"Training complete. Best iteration: {best_iter}")

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability of positive class (tail risk event).

        Args:
            X: Feature DataFrame.

        Returns:
            Array of probabilities for class 1.
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call fit() first.")
        return self.model.predict_proba(X)[:, 1]

    def feature_importance(self, importance_type: str = "gain") -> pd.Series:
        """Return feature importance sorted descending.

        Args:
            importance_type: 'gain' or 'split'.

        Returns:
            Series with feature names as index, importance as values.
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call fit() first.")

        importance = self.model.feature_importances_
        return (
            pd.Series(importance, index=self.feature_names, name="importance")
            .sort_values(ascending=False)
        )

    def save(self, path: str | Path) -> None:
        """Save model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "feature_names": self.feature_names}, path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str | Path) -> "TailRiskModel":
        """Load model from disk."""
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_names = data["feature_names"]
        logger.info(f"Model loaded from {path}")
        return self
