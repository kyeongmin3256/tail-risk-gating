# TailCast

ML-driven tail-risk gating for short-volatility and macro allocation strategies.

TailCast estimates daily conditional tail-loss probability from market features and converts it into deterministic gating actions: trade, reduce exposure, or move to cash.

## Problem

Short-vol and carry strategies can fail abruptly when volatility regimes shift. TailCast answers:

> *Should risk be taken today, given current tail-risk conditions?*

## Architecture

```
Yahoo Finance + FRED
        │
        ▼
Feature engineering (25+ signals)
        │
        ▼
LightGBM + walk-forward validation + calibration
        │
        ├── SHAP explainability
        ├── Gated vs ungated backtest
        └── Significance testing (moving-block bootstrap)
        │
        ▼
FastAPI + React dashboard
```

## Results

Walk-forward gated vs ungated evaluation (-4% loss threshold):

| Metric | Ungated | Gated | Change |
|--------|---------|-------|--------|
| Sharpe | 0.89 | **0.94** | +5.6% |
| CVaR (95%) | -1.05% | **-1.01%** | 4.2% tail-risk reduction |
| Annual return | 5.79% | 5.90% | +1.9% |

Out-of-sample significance (soft gate @ 0.20, -2% threshold): Sharpe delta **+0.19**, CVaR improvement **+0.006**.

## Tech Stack

- Python, LightGBM, pandas, NumPy/SciPy
- Walk-forward retraining, isotonic/Platt calibration
- SHAP feature attribution
- FastAPI, React, Tailwind, Recharts
- PostgreSQL (optional), Docker Compose

## Project Structure

```
src/
  data/         # market data ingestion
  features/     # volatility, credit, momentum, calendar
  models/       # LightGBM, walk-forward, calibration
  evaluation/   # backtesting, gating engine, metrics
  api/          # FastAPI serving layer
frontend/       # dashboard UI
```

## Quick Start

```bash
git clone https://github.com/kyeongmin3256/tail-risk-gating.git
cd tail-risk-gating
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python run_pipeline.py
python run_training.py
```

Docker (API + dashboard + Postgres):

```bash
docker compose up -d
uvicorn src.api.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Daily model refresh:

```bash
./scripts/run_daily_refresh.sh
```

## Downstream Integration

MacroShift consumes `tail_risk_prob` from `data/model_outputs/wf_predictions.csv` as an exposure overlay on ETF allocation. See MacroShift `docs/tailcast_integration_template.md`.

## License

MIT
