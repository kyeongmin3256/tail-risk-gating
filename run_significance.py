"""Bootstrap significance test for gated vs ungated strategy metrics.

Uses paired moving-block bootstrap on daily returns to estimate confidence
intervals and p-values for:
  - Sharpe improvement: Sharpe(gated) - Sharpe(ungated)
  - CVaR improvement: |CVaR(ungated)| - |CVaR(gated)|

Examples:
  python run_significance.py --threshold 4 --gate-threshold 0.15 --gating-mode hard
  python run_significance.py --threshold 4 --gate-threshold 0.15 --gating-mode soft
  python run_significance.py --sweep --thresholds 2 4 6 8 --gate-thresholds 0.10 0.15 0.20
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.evaluation.gating import apply_gating


def annualized_sharpe(returns: np.ndarray) -> float:
    std = returns.std(ddof=1)
    if std == 0 or np.isnan(std):
        return 0.0
    return float((returns.mean() / std) * np.sqrt(252))


def cvar_5pct(returns: np.ndarray, alpha: float = 0.05) -> float:
    q = np.quantile(returns, alpha)
    tail = returns[returns <= q]
    if len(tail) == 0:
        return float(q)
    return float(tail.mean())


def moving_block_indices(n: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, max(n - block_size + 1, 1), size=int(np.ceil(n / block_size)))
    idx = np.concatenate([np.arange(s, min(s + block_size, n)) for s in starts])[:n]
    return idx


def load_returns(
    root: Path,
    threshold: int,
    gate_threshold: float,
    gating_mode: str,
) -> tuple[np.ndarray, np.ndarray]:
    preds_path = root / f"outputs/threshold_-{threshold}/wf_predictions_calibrated.csv"
    fwd_path = root / "data/processed/target_continuous.csv"

    preds = pd.read_csv(preds_path, index_col=0, parse_dates=True).squeeze("columns")
    fwd = pd.read_csv(fwd_path, index_col="date", parse_dates=True).squeeze("columns")

    common = preds.index.intersection(fwd.index)
    p = preds.loc[common].astype(float)
    r = fwd.loc[common].astype(float)
    valid = p.notna() & r.notna() & np.isfinite(p) & np.isfinite(r)
    p = p[valid]
    r = r[valid]

    ungated = r.values
    gated_series = apply_gating(r, p, gate_threshold, gating_mode)
    gated = gated_series.values
    return gated, ungated


def summarize(gated: np.ndarray, ungated: np.ndarray) -> dict:
    sharpe_g = annualized_sharpe(gated)
    sharpe_u = annualized_sharpe(ungated)
    cvar_g = cvar_5pct(gated)
    cvar_u = cvar_5pct(ungated)
    return {
        "sharpe_gated": sharpe_g,
        "sharpe_ungated": sharpe_u,
        "sharpe_diff": sharpe_g - sharpe_u,
        "cvar_gated": cvar_g,
        "cvar_ungated": cvar_u,
        "cvar_improvement": abs(cvar_u) - abs(cvar_g),
    }


def run_single(
    *,
    root: Path,
    threshold: int,
    gate_threshold: float,
    gating_mode: str,
    bootstrap_samples: int,
    block_size: int,
    seed: int,
) -> dict:
    gated, ungated = load_returns(root, threshold, gate_threshold, gating_mode)
    n = len(gated)
    rng = np.random.default_rng(seed)
    obs = summarize(gated, ungated)

    sharpe_diffs = np.empty(bootstrap_samples)
    cvar_improvements = np.empty(bootstrap_samples)
    for i in range(bootstrap_samples):
        idx = moving_block_indices(n, block_size, rng)
        s = summarize(gated[idx], ungated[idx])
        sharpe_diffs[i] = s["sharpe_diff"]
        cvar_improvements[i] = s["cvar_improvement"]

    def ci(arr: np.ndarray) -> tuple[float, float]:
        lo, hi = np.quantile(arr, [0.025, 0.975])
        return float(lo), float(hi)

    sharpe_ci = ci(sharpe_diffs)
    cvar_ci = ci(cvar_improvements)
    sharpe_p = float((sharpe_diffs <= 0).mean())
    cvar_p = float((cvar_improvements <= 0).mean())

    return {
        "config": {
            "threshold": threshold,
            "gate_threshold": gate_threshold,
            "gating_mode": gating_mode,
            "bootstrap_samples": bootstrap_samples,
            "block_size": block_size,
            "seed": seed,
            "n_days": n,
        },
        "observed": obs,
        "bootstrap": {
            "sharpe_diff_ci95": {"low": sharpe_ci[0], "high": sharpe_ci[1]},
            "cvar_improvement_ci95": {"low": cvar_ci[0], "high": cvar_ci[1]},
            "sharpe_improvement_pvalue_onesided": sharpe_p,
            "cvar_improvement_pvalue_onesided": cvar_p,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=4, help="Loss threshold bucket: 2, 4, 6, 8.")
    p.add_argument("--thresholds", type=int, nargs="*", default=[2, 4, 6, 8])
    p.add_argument("--gate-threshold", type=float, default=0.15)
    p.add_argument("--gate-thresholds", type=float, nargs="*", default=[0.10, 0.15, 0.20, 0.25, 0.30])
    p.add_argument("--gating-mode", choices=["hard", "soft"], default="hard")
    p.add_argument("--compare-modes", action="store_true", help="Run both hard and soft for one threshold.")
    p.add_argument("--sweep", action="store_true", help="Run grid sweep and save CSV summary.")
    p.add_argument("--bootstrap-samples", type=int, default=5000)
    p.add_argument("--block-size", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-json", type=Path, default=Path("data/model_outputs/significance_test.json"))
    p.add_argument("--output-csv", type=Path, default=Path("data/model_outputs/significance_sweep.csv"))
    args = p.parse_args()

    root = Path(__file__).resolve().parent
    if args.sweep:
        rows: list[dict] = []
        for th in args.thresholds:
            for gate in args.gate_thresholds:
                modes = ["hard", "soft"] if args.compare_modes else [args.gating_mode]
                for mode in modes:
                    out = run_single(
                        root=root,
                        threshold=th,
                        gate_threshold=gate,
                        gating_mode=mode,
                        bootstrap_samples=args.bootstrap_samples,
                        block_size=args.block_size,
                        seed=args.seed,
                    )
                    rows.append(
                        {
                            "threshold": th,
                            "gate_threshold": gate,
                            "gating_mode": mode,
                            "n_days": out["config"]["n_days"],
                            "sharpe_gated": out["observed"]["sharpe_gated"],
                            "sharpe_ungated": out["observed"]["sharpe_ungated"],
                            "sharpe_diff": out["observed"]["sharpe_diff"],
                            "sharpe_ci_low": out["bootstrap"]["sharpe_diff_ci95"]["low"],
                            "sharpe_ci_high": out["bootstrap"]["sharpe_diff_ci95"]["high"],
                            "sharpe_p": out["bootstrap"]["sharpe_improvement_pvalue_onesided"],
                            "cvar_improvement": out["observed"]["cvar_improvement"],
                            "cvar_ci_low": out["bootstrap"]["cvar_improvement_ci95"]["low"],
                            "cvar_ci_high": out["bootstrap"]["cvar_improvement_ci95"]["high"],
                            "cvar_p": out["bootstrap"]["cvar_improvement_pvalue_onesided"],
                        }
                    )
        df = pd.DataFrame(rows).sort_values(["threshold", "gate_threshold", "gating_mode"])
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output_csv, index=False)
        print(df.to_string(index=False))
        print(f"\nSaved sweep results to {args.output_csv}")
        return

    if args.compare_modes:
        outs = []
        for mode in ["hard", "soft"]:
            outs.append(
                run_single(
                    root=root,
                    threshold=args.threshold,
                    gate_threshold=args.gate_threshold,
                    gating_mode=mode,
                    bootstrap_samples=args.bootstrap_samples,
                    block_size=args.block_size,
                    seed=args.seed,
                )
            )
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps({"results": outs}, indent=2), encoding="utf-8")
        print(json.dumps({"results": outs}, indent=2))
        return

    out = run_single(
        root=root,
        threshold=args.threshold,
        gate_threshold=args.gate_threshold,
        gating_mode=args.gating_mode,
        bootstrap_samples=args.bootstrap_samples,
        block_size=args.block_size,
        seed=args.seed,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
