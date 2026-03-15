"""Evaluation metrics for tail risk probability estimation.

Standard accuracy is meaningless at ~6.5% positive rate.
Instead we focus on:
    - Brier score (probability calibration quality)
    - AUC-ROC and AUC-PR (ranking quality)
    - Precision-Recall at various thresholds
    - Calibration curve (reliability diagram)

Usage:
    from src.evaluation.metrics import evaluate_predictions
    report = evaluate_predictions(y_true, y_prob)
"""

import logging

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_recall_curve,
    roc_auc_score,
)

logger = logging.getLogger(__name__)


def evaluate_predictions(
    y_true: np.ndarray,
    y_prob: np.ndarray,
) -> dict:
    """Compute all evaluation metrics.

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities for positive class.

    Returns:
        Dictionary of metric name → value.
    """
    metrics = {
        "n_samples": len(y_true),
        "n_positive": int(y_true.sum()),
        "positive_rate": float(y_true.mean()),
        "brier_score": brier_score_loss(y_true, y_prob),
        "log_loss": log_loss(y_true, y_prob),
        "roc_auc": roc_auc_score(y_true, y_prob),
        "avg_precision": average_precision_score(y_true, y_prob),
        "mean_predicted_prob": float(y_prob.mean()),
    }

    # Precision at key recall levels
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    for target_recall in [0.5, 0.7, 0.9]:
        mask = recall >= target_recall
        if mask.any():
            metrics[f"precision_at_recall_{target_recall}"] = float(
                precision[mask][-1]
            )

    return metrics


def calibration_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> pd.DataFrame:
    """Compute calibration curve data (reliability diagram).

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities.
        n_bins: Number of probability bins.

    Returns:
        DataFrame with columns: bin_mid, mean_predicted, mean_actual, count.
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    rows = []
    for i in range(n_bins):
        mask = bin_indices == i
        if mask.sum() > 0:
            rows.append({
                "bin_mid": (bins[i] + bins[i + 1]) / 2,
                "mean_predicted": float(y_prob[mask].mean()),
                "mean_actual": float(y_true[mask].mean()),
                "count": int(mask.sum()),
            })

    return pd.DataFrame(rows)


def format_report(metrics: dict) -> str:
    """Format metrics as a readable report string.

    Args:
        metrics: Dictionary from evaluate_predictions().

    Returns:
        Formatted multi-line string.
    """
    lines = [
        "=" * 50,
        "TAIL RISK MODEL EVALUATION",
        "=" * 50,
        f"Samples: {metrics['n_samples']} "
        f"({metrics['n_positive']} positive, "
        f"{metrics['positive_rate']:.1%} rate)",
        "",
        "Calibration:",
        f"  Brier Score:    {metrics['brier_score']:.4f}  (lower = better)",
        f"  Log Loss:       {metrics['log_loss']:.4f}",
        f"  Mean Predicted:  {metrics['mean_predicted_prob']:.4f}",
        "",
        "Ranking:",
        f"  ROC-AUC:         {metrics['roc_auc']:.4f}",
        f"  Avg Precision:   {metrics['avg_precision']:.4f}",
        "",
        "Precision at Recall:",
    ]

    for key, val in metrics.items():
        if key.startswith("precision_at_recall_"):
            recall_level = key.split("_")[-1]
            lines.append(f"  Recall {recall_level}: Precision = {val:.4f}")

    lines.append("=" * 50)
    return "\n".join(lines)
