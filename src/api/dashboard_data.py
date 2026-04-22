"""Build dashboard payload from model output artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

THRESHOLDS = [2, 4, 6, 8]
GATE_THRESHOLD = 0.15
EQUITY_SAMPLE = 10

FEATURE_LABELS = {
    "rvol_5d": "5d Realized Vol",
    "rvol_10d": "10d Realized Vol",
    "rvol_20d": "20d Realized Vol",
    "vix": "VIX Level",
    "vvix": "VVIX",
    "skew": "SKEW Index",
    "iv_rv_spread": "IV-RV Spread",
    "vix_term_slope": "VIX Term Slope",
    "vix_term_inverted": "VIX Term Inverted",
    "vix9d_vix_ratio": "VIX9D/VIX Ratio",
    "credit_spread": "Credit Spread",
    "dxy_mom_5d": "DXY 5d Mom",
    "dxy_mom_20d": "DXY 20d Mom",
    "spy_ret_1d": "SPY 1d Return",
    "spy_ret_5d": "SPY 5d Return",
    "spy_ret_10d": "SPY 10d Return",
    "spy_ret_20d": "SPY 20d Return",
    "dist_from_ma": "Dist from 50d MA",
    "volume_ratio": "Volume Ratio",
    "max_drawdown_5d": "5d Max Drawdown",
    "consec_down_days": "Consec Down Days",
    "max_move_20d": "20d Max Move",
    "days_to_fomc": "Days to FOMC",
    "earnings_season": "Earnings Season",
    "days_to_opex": "Days to OpEx",
}

RISK_DECREASING = {
    "spy_ret_5d",
    "spy_ret_10d",
    "spy_ret_20d",
    "spy_ret_1d",
    "dist_from_ma",
    "dxy_mom_5d",
    "dxy_mom_20d",
}


def _shap_direction(feature: str, mean_shap: float) -> str:
    if abs(mean_shap) < 1e-4:
        return "mixed"
    if feature in RISK_DECREASING:
        return "risk_decreasing" if mean_shap > 0 else "risk_increasing"
    return "risk_increasing" if mean_shap > 0 else "risk_decreasing"


def _build_roc_curve(actuals: np.ndarray, preds: np.ndarray, n_points: int = 20) -> list[dict]:
    fpr_arr, tpr_arr, _ = roc_curve(actuals, preds)
    idx = np.linspace(0, len(fpr_arr) - 1, n_points, dtype=int)
    pts = [{"fpr": round(float(fpr_arr[i]), 4), "tpr": round(float(tpr_arr[i]), 4)} for i in idx]
    if pts[0] != {"fpr": 0.0, "tpr": 0.0}:
        pts.insert(0, {"fpr": 0.0, "tpr": 0.0})
    if pts[-1] != {"fpr": 1.0, "tpr": 1.0}:
        pts.append({"fpr": 1.0, "tpr": 1.0})
    return pts


def _build_fold_stats(fold_df: pd.DataFrame, preds: pd.Series, actuals: pd.Series) -> list[dict]:
    rows: list[dict] = []
    for _, fold in fold_df.iterrows():
        start = pd.Timestamp(fold["test_start"])
        end = pd.Timestamp(fold["test_end"])
        mask = (preds.index >= start) & (preds.index <= end)
        p = preds[mask].values
        a = actuals[mask].values
        if a.sum() >= 2 and len(np.unique(a)) > 1:
            try:
                auc = round(float(roc_auc_score(a, p)), 3)
            except Exception:
                auc = None
        else:
            auc = None
        period = f"{start.year}–{end.year}" if start.year != end.year else str(start.year)
        rows.append(
            {
                "fold": int(fold["fold"]) + 1,
                "period": period,
                "auc": auc,
                "samples": int(fold["test_size"]),
                "positives": int(round(fold["pos_rate_test"] * fold["test_size"])),
            }
        )
    return rows


def _build_equity_curve(preds: pd.Series, fwd: pd.Series) -> tuple[list[dict], list[dict]]:
    common = preds.index.intersection(fwd.index)
    p = preds.loc[common]
    r = fwd.loc[common]
    ungated_cum = (1 + r).cumprod()
    gate_mask = p <= GATE_THRESHOLD
    gated_r = r.copy()
    gated_r[~gate_mask] = 0.0
    gated_cum = (1 + gated_r).cumprod()
    ungated_cum /= ungated_cum.iloc[0]
    gated_cum /= gated_cum.iloc[0]

    def drawdown(cum: pd.Series) -> pd.Series:
        roll_max = cum.cummax()
        return (cum - roll_max) / roll_max

    ungated_dd = drawdown(ungated_cum)
    gated_dd = drawdown(gated_cum)
    idx = list(range(0, len(ungated_cum), EQUITY_SAMPLE))
    if idx and idx[-1] != len(ungated_cum) - 1:
        idx.append(len(ungated_cum) - 1)

    def fmt_date(ts: pd.Timestamp) -> str:
        return ts.strftime("%Y-%m")

    equity = [
        {
            "date": fmt_date(ungated_cum.index[i]),
            "gated": round(float(gated_cum.iloc[i]), 4),
            "ungated": round(float(ungated_cum.iloc[i]), 4),
        }
        for i in idx
    ]
    drawdowns = [
        {
            "date": fmt_date(ungated_dd.index[i]),
            "gated": round(float(gated_dd.iloc[i]), 4),
            "ungated": round(float(ungated_dd.iloc[i]), 4),
        }
        for i in idx
    ]
    return equity, drawdowns


def _safe(row: pd.Series, col: str, default: float = 0.0) -> float:
    v = row.get(col, default)
    return float(v) if pd.notna(v) else default


def _to_summary(row: pd.Series, n_total: int) -> dict:
    tr = _safe(row, "total_return")
    n_days = int(_safe(row, "n_days", n_total))
    ann = (1 + tr) ** (252 / max(n_days, 1)) - 1 if n_days > 0 else 0
    mdd = _safe(row, "max_drawdown")
    sharpe = _safe(row, "sharpe")
    calmar = abs(ann / mdd) if mdd != 0 else 0
    days_skipped = int(_safe(row, "days_skipped", 0))
    return {
        "totalReturn": round(1 + tr, 4),
        "annualizedReturn": round(ann, 4),
        "sharpe": round(sharpe, 4),
        "maxDrawdown": round(mdd, 4),
        "calmar": round(calmar, 4),
        "tradingDays": n_days,
        "daysGated": days_skipped,
    }


def process_threshold(t: int, fwd_returns: pd.Series, root_dir: Path) -> dict:
    out_dir = root_dir / f"outputs/threshold_-{t}"
    summary = pd.read_csv(out_dir / "summary.csv", header=None, index_col=0).squeeze()
    preds_cal = pd.read_csv(out_dir / "wf_predictions_calibrated.csv", index_col=0, parse_dates=True).squeeze()
    preds_raw = pd.read_csv(out_dir / "wf_predictions.csv", index_col=0, parse_dates=True).squeeze()
    actuals = pd.read_csv(out_dir / "wf_actuals.csv", index_col=0, parse_dates=True).squeeze()
    fold_df = pd.read_csv(out_dir / "fold_stats.csv", parse_dates=["test_start", "test_end"])
    bt_df = pd.read_csv(out_dir / "backtest_results.csv")
    cal_df = pd.read_csv(out_dir / "calibration_curve.csv")
    shap_df = pd.read_csv(out_dir / "shap_values.csv", index_col=0, parse_dates=True)

    last_date = preds_cal.index[-1]
    last_prob = float(preds_cal.iloc[-1])
    shap_row = shap_df.loc[last_date] if last_date in shap_df.index else shap_df.iloc[-1]
    mean_shap = shap_df.abs().mean()
    top5_features = mean_shap.nlargest(5).index.tolist()
    top_drivers = []
    for feat in top5_features:
        raw_val = float(shap_row.get(feat, 0))
        top_drivers.append(
            {
                "feature": feat,
                "label": FEATURE_LABELS.get(feat, feat),
                "shapValue": round(raw_val, 4),
                "direction": _shap_direction(feat, raw_val),
            }
        )

    today_risk = {
        "date": last_date.strftime("%Y-%m-%d"),
        "probability": round(last_prob, 4),
        "topDrivers": top_drivers,
        "modelInfo": {
            "dataThrough": last_date.strftime("%Y-%m-%d"),
            "nFolds": int(len(fold_df)),
            "windowSize": "756+ trading days",
        },
    }

    common = preds_raw.index.intersection(actuals.index).dropna()
    p_arr = preds_raw.loc[common].values.astype(float)
    a_arr = actuals.loc[common].values.astype(float)
    roc_pts = _build_roc_curve(a_arr, p_arr) if len(np.unique(a_arr)) > 1 else []
    folds_data = _build_fold_stats(fold_df, preds_raw, actuals)
    model_metrics = {
        "rocAuc": round(float(summary.get("raw_roc_auc", 0)), 4),
        "avgPrecision": round(float(summary.get("raw_avg_precision", 0)), 4),
        "brierScore": round(float(summary.get("raw_brier_score", 0)), 4),
        "rocCurve": roc_pts,
        "walkForwardFolds": folds_data,
        "calibration": {
            "predicted": [round(float(v), 4) for v in cal_df["mean_predicted"]],
            "observed": [round(float(v), 4) for v in cal_df["mean_actual"]],
        },
    }

    mean_abs = shap_df.abs().mean().sort_values(ascending=False)
    mean_signed = shap_df.mean()
    shap_values = [
        {
            "feature": FEATURE_LABELS.get(feat, feat),
            "rawFeature": feat,
            "importance": round(float(importance), 5),
            "direction": _shap_direction(feat, float(mean_signed[feat])),
        }
        for feat, importance in mean_abs.items()
    ]

    ungated_row = bt_df[bt_df["strategy"].str.startswith("ungated")].iloc[0]
    gated_candidates = bt_df[bt_df["gate_threshold"].notna()].copy()
    gated_row = None
    if len(gated_candidates) > 0:
        closest = (gated_candidates["gate_threshold"] - GATE_THRESHOLD).abs().idxmin()
        gated_row = gated_candidates.loc[closest]

    n_total = int(_safe(ungated_row, "n_days", len(preds_raw)))
    ungated_summary = _to_summary(ungated_row, n_total)
    gated_summary = _to_summary(gated_row, n_total) if gated_row is not None else ungated_summary
    fwd = fwd_returns.reindex(preds_cal.index).dropna()
    equity_curve, drawdown_series = _build_equity_curve(preds_cal, fwd)

    backtest_results = {
        "summary": {"gated": gated_summary, "ungated": ungated_summary},
        "equityCurve": equity_curve,
        "drawdownSeries": drawdown_series,
    }

    return {
        "todayRisk": today_risk,
        "modelMetrics": model_metrics,
        "shapValues": shap_values,
        "backtestResults": backtest_results,
    }


def load_dashboard_data(root_dir: Path) -> dict:
    fwd_returns = pd.read_csv(
        root_dir / "data/processed/target_continuous.csv",
        index_col="date",
        parse_dates=True,
    ).squeeze()
    data_by_threshold = {str(t): process_threshold(t, fwd_returns, root_dir) for t in THRESHOLDS}
    return {"thresholds": THRESHOLDS, "dataByThreshold": data_by_threshold}
