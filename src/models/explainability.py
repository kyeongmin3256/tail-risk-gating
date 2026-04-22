"""SHAP-based model explainability.

Computes SHAP values to explain which features drive tail risk
predictions on each day. Supports both global importance and
per-prediction explanations.

Usage:
    from src.models.explainability import SHAPExplainer
    explainer = SHAPExplainer(model)
    shap_values = explainer.compute(X_test)
    explainer.summary_plot(shap_values, X_test)
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import shap

from src.models.trainer import TailRiskModel

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """SHAP-based feature importance and explanation."""

    def __init__(self, model: TailRiskModel):
        """Initialize with a trained model.

        Args:
            model: Trained TailRiskModel instance.
        """
        if model.model is None:
            raise RuntimeError("Model must be trained before computing SHAP values.")

        self.model = model
        self._explainer = shap.TreeExplainer(model.model)

    def compute(self, X: pd.DataFrame) -> np.ndarray:
        """Compute SHAP values for all samples.

        Args:
            X: Feature DataFrame.

        Returns:
            Array of SHAP values, shape (n_samples, n_features).
        """
        shap_values = self._explainer.shap_values(X)

        # TreeExplainer returns [class_0, class_1] for binary
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        logger.info(f"SHAP values computed for {len(X)} samples")
        return shap_values

    def global_importance(self, shap_values: np.ndarray, X: pd.DataFrame) -> pd.Series:
        """Compute mean absolute SHAP value per feature (global importance).

        Args:
            shap_values: SHAP values from compute().
            X: Feature DataFrame (for column names).

        Returns:
            Series sorted by importance.
        """
        mean_abs = np.abs(shap_values).mean(axis=0)
        return (
            pd.Series(mean_abs, index=X.columns, name="mean_abs_shap")
            .sort_values(ascending=False)
        )

    def explain_single(
        self, shap_values: np.ndarray, X: pd.DataFrame, idx: int
    ) -> pd.DataFrame:
        """Explain a single prediction.

        Args:
            shap_values: SHAP values from compute().
            X: Feature DataFrame.
            idx: Row index to explain.

        Returns:
            DataFrame with feature name, value, and SHAP contribution.
        """
        return (
            pd.DataFrame({
                "feature": X.columns,
                "value": X.iloc[idx].values,
                "shap_value": shap_values[idx],
            })
            .sort_values("shap_value", key=abs, ascending=False)
            .reset_index(drop=True)
        )

    def top_risk_drivers(
        self,
        shap_values: np.ndarray,
        X: pd.DataFrame,
        idx: int,
        top_n: int = 5,
    ) -> pd.DataFrame:
        """Return top N features driving a specific prediction.

        Useful for daily risk reports: "Today's elevated risk is
        driven by VIX term structure inversion and credit spread widening."

        Args:
            shap_values: SHAP values from compute().
            X: Feature DataFrame.
            idx: Row index.
            top_n: Number of top features to return.

        Returns:
            DataFrame with top risk-driving features.
        """
        explanation = self.explain_single(shap_values, X, idx)
        # Only positive SHAP = pushes toward tail risk
        risk_drivers = explanation[explanation["shap_value"] > 0].head(top_n)
        return risk_drivers

    def save_values(
        self,
        shap_values: np.ndarray,
        X: pd.DataFrame,
        path: str | Path,
    ) -> None:
        """Save SHAP values to CSV.

        Args:
            shap_values: SHAP values array.
            X: Feature DataFrame (for index and column names).
            path: Output file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(shap_values, index=X.index, columns=X.columns)
        df.to_csv(path)
        logger.info(f"SHAP values saved to {path}")
