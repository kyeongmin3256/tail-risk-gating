# TailCast — Project Roadmap

## Resume Bullets

**TailCast** — *Calibrated Machine Learning for Conditional Loss Probability Estimation in Short-Volatility Strategies* | Sep. 2025 – Present

- Built a daily trade-gating signal system converting calibrated tail-loss probabilities into deterministic reduce/skip actions for short-volatility strategies.
- Built a Python + PostgreSQL data pipeline (pandas) to ingest and validate 18+ years of market data across 9 instruments.
- Developed calibrated LightGBM classifiers (isotonic/Platt) to estimate conditional tail-loss probabilities for short-volatility strategies.
- Engineered 25 predictive features (volatility term structure, credit stress, momentum, calendar effects) using NumPy/SciPy.
- Implemented expanding-window walk-forward backtesting with SHAP explainability and multi-threshold models (-2%/-4%/-6%/-8%); improved gated-vs-ungated Sharpe by 5.55% and reduced CVaR(95) by 4.16%.

---

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
- Auto-refresh README metrics from `gating_primary.csv`

## PostgreSQL

Raw market data can be persisted in PostgreSQL alongside CSV cache.

```bash
docker compose up -d db
python3 scripts/init_db.py
python3 scripts/migrate_csv_to_db.py   # one-time import from data/raw
python3 run_pipeline.py --use-cache    # prefers PostgreSQL when populated
python3 run_pipeline.py                # fetch + write CSV + PostgreSQL
```
