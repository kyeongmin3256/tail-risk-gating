"""Probability calibration for tail risk predictions.

Raw LightGBM outputs are not calibrated probabilities.
This module applies isotonic regression or Platt scaling
to produce meaningful P(tail event | features).

A well-calibrated model means: when it says 10% risk,
~10% of those days actually experience a tail event.

Usage:
    from src.models.calibration import CalibratedModel
    cal_model = CalibratedModel(method="isotonic")
    cal_model.fit(raw_probs_val, y_val)
    calibrated = cal_model.transform(raw_probs_test)
"""

import logging

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)


class CalibratedModel:
    """Post-hoc probability calibration.

    Fits a calibration mapping on validation data, then transforms
    raw model outputs to calibrated probabilities.
    """

    def __init__(self, method: str = "isotonic"):
        """Initialize calibrator.

        Args:
            method: 'isotonic' for isotonic regression (non-parametric),
                    'platt' for Platt scaling (logistic regression).
        """
        if method not in ("isotonic", "platt"):
            raise ValueError(f"Unknown method: {method}. Use 'isotonic' or 'platt'.")

        self.method = method
        self._calibrator = None

    def fit(self, raw_probs: np.ndarray, y_true: np.ndarray) -> "CalibratedModel":
        """Fit calibration mapping on held-out data.

        Args:
            raw_probs: Raw predicted probabilities from the model.
            y_true: True binary labels.

        Returns:
            self for chaining.
        """
        if self.method == "isotonic":
            self._calibrator = IsotonicRegression(
                y_min=0.0, y_max=1.0, out_of_bounds="clip"
            )
            self._calibrator.fit(raw_probs, y_true)
        else:
            # Platt scaling: logistic regression on raw probs
            self._calibrator = LogisticRegression(C=1.0, solver="lbfgs")
            self._calibrator.fit(raw_probs.reshape(-1, 1), y_true)

        logger.info(f"Calibration fitted ({self.method}) on {len(y_true)} samples")
        return self

    def transform(self, raw_probs: np.ndarray) -> np.ndarray:
        """Apply calibration to raw probabilities.

        Args:
            raw_probs: Raw predicted probabilities.

        Returns:
            Calibrated probabilities.
        """
        if self._calibrator is None:
            raise RuntimeError("Calibrator not fitted. Call fit() first.")

        if self.method == "isotonic":
            return self._calibrator.transform(raw_probs)
        else:
            return self._calibrator.predict_proba(raw_probs.reshape(-1, 1))[:, 1]

    def fit_transform(self, raw_probs: np.ndarray, y_true: np.ndarray) -> np.ndarray:
        """Fit and transform in one call."""
        self.fit(raw_probs, y_true)
        return self.transform(raw_probs)
