# TailCast — Project Roadmap

## Resume Bullets

**TailCast** — *Calibrated Machine Learning for Conditional Loss Probability Estimation in Short-Volatility Strategies* | Sep. 2025 – Present

- Built a daily trade-gating signal system converting calibrated tail-loss probabilities into deterministic reduce/skip actions for short-volatility strategies.
- Built a Python + PostgreSQL data pipeline (pandas) to ingest and validate 18+ years of market data across 9 instruments, with CSV cache fallback and Dockerized API/dashboard serving.
- Developed calibrated LightGBM classifiers (isotonic/Platt) to estimate conditional tail-loss probabilities for short-volatility strategies.
- Engineered 25 predictive features (volatility term structure, credit stress, momentum, calendar effects) using NumPy/SciPy.
- Implemented expanding-window walk-forward backtesting with SHAP explainability and multi-threshold models (-2%/-4%/-6%/-8%); soft gating (-2% @ 20%) lifted gated Sharpe from 2.07 → 2.16 (+4.6%) and cut CVaR(95) by 10% on a short-straddle proxy (~3,045 days), with +0.19 OOT Sharpe delta over the last 756 days (`outputs/threshold_-2/gating_primary.csv`).

---

## Canonical metrics (single source of truth)

| Claim | Value | Artifact |
|-------|-------|----------|
| Headline gate | soft **-2% @ 20%** | `outputs/threshold_-2/gating_primary.csv` |
| Ungated / gated Sharpe | **2.07** / **2.16** (**+4.6%**) | same |
| CVaR(95) ungated → gated | **-3.29%** → **-2.96%** (**10%** risk reduction) | same |
| OOT Sharpe delta / CVaR improvement | **+0.19** / **+0.006** (last 756d @ 20%) | `data/model_outputs/significance_oot_t2_soft.csv` |

Refresh after retrain:

```bash
python3 scripts/refresh_gating_primary.py
python3 scripts/update_readme_metrics.py
```

## Current Status

Model pipeline, significance testing, FastAPI serving, and React dashboard are complete.

**Recently added**
- Shared soft/hard gating engine (`src/evaluation/gating.py`)
- Per-threshold gating policy (`-2%` soft @ 0.20, `-4/-6/-8%` hard @ 0.15)
- Short Straddle B&H benchmark labeling in backtests and dashboard
- Docker Compose stack (API + frontend + Postgres)
- `scripts/refresh_gating_primary.py` to regenerate gating summaries from existing model outputs

**Next phase**
- Cloud deployment (EC2/RDS or managed Postgres)
- README metrics auto-refresh wired into CI (`scripts/update_readme_metrics.py`)

**Automation**
- Weekday daily refresh: `./scripts/run_daily_refresh.sh` (fetch → train → `wf_predictions.csv`)
- macOS scheduler: `./scripts/setup_daily_refresh_launchd.sh` (default weekdays 06:00)
- MacroShift merge runs separately at 07:00 via `MacroShift/scripts/run_tailcast_pipeline.sh`

## PostgreSQL

Raw market data can be persisted in PostgreSQL alongside CSV cache.

```bash
docker compose up -d db
python3 scripts/init_db.py
python3 scripts/migrate_csv_to_db.py   # one-time import from data/raw
python3 run_pipeline.py --use-cache    # prefers PostgreSQL when populated
python3 run_pipeline.py                # fetch + write CSV + PostgreSQL
```
