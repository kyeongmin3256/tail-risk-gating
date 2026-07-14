# TailCast

Calibrated machine learning for **conditional tail-loss probability** — and deterministic trade gating — for short-volatility strategies.

> *Should risk be taken today, given current tail-risk conditions?*

TailCast turns daily market features into a calibrated `tail_risk_prob`, then maps that probability into **trade / reduce / cash** actions for a short ATM SPY straddle proxy.

### Dashboard demo

~20s walkthrough of the research monitor — live tail-risk probability, loss-tolerance controls, SHAP drivers, and gated backtest panels.

<video src="assets/tailcast-dashboard-demo.mp4" controls width="100%"></video>

[Download MP4](assets/tailcast-dashboard-demo.mp4)

---

## Problem

Short-vol and carry strategies earn steady premia until a volatility regime shift — then losses arrive abruptly. Rules based on raw VIX levels are brittle; uncalibrated ML scores are hard to turn into position sizing.

TailCast is built to answer an operational question with a probabilistic one:

1. Estimate **P(tail loss | features)** under a chosen loss threshold.
2. Calibrate so probability is usable as an exposure dial.
3. Gate the strategy with a fixed, audited policy (soft or hard).

---

## Method

| Stage | What happens |
|-------|----------------|
| Data | Yahoo Finance + FRED from **2006–** (SPY, VIX complex, SKEW, HYG, IEF, UUP, rates) |
| Target | Forward short-straddle proxy P&L; binary labels at **-2 / -4 / -6 / -8%** loss buckets |
| Model | **LightGBM** + expanding-window walk-forward (~quarterly retrain) |
| Calibration | Isotonic / Platt so `tail_risk_prob` is decision-ready |
| Gate | Soft (scale exposure) or hard (trade / skip) by threshold policy |
| Eval | Gated vs ungated Sharpe / CVaR, SHAP, moving-block bootstrap + OOT window |

**Default gate policy**

| Loss bucket | Mode | Gate threshold |
|-------------|------|----------------|
| -2% | soft | 0.20 |
| -4% / -6% / -8% | hard | 0.15 |

---

## Core Results

<!-- METRICS:START -->
### Best full-sample profile — soft gate (-2% @ 20%) vs Short Straddle B&H

Walk-forward evaluation on the short ATM SPY straddle proxy (~2,990 days).

| Metric | Ungated (B&H) | Gated | Change |
|--------|---------------|-------|--------|
| Sharpe | 1.94 | **2.03** | **+4.3%** |
| CVaR (95%) | -3.31% | **-2.85%** | **14%** tail-risk reduction |

### Out-of-sample check — soft gate (-2% @ 20%, last 756 days)

| Diagnostic | Value |
|------------|-------|
| Sharpe delta (gated − ungated) | **+0.19** |
| CVaR improvement | **+0.006** |

### Headline vs deeper buckets

Deeper loss buckets (-4% and below) use a **hard** gate @ 15%. They are useful stress labels for the dashboard, but the **resume / portfolio headline** is the **-2% soft @ 20%** profile above (best risk-adjusted gated-vs-ungated tradeoff in current artifacts).

Artifacts: `outputs/threshold_-2/gating_primary.csv`, `data/model_outputs/significance_oot_t2_soft.csv`, `data/model_outputs/significance_sweep_t2_soft.csv`
<!-- METRICS:END -->

Refresh metrics after a retrain:

```bash
python3 scripts/refresh_gating_primary.py
python3 scripts/update_readme_metrics.py
```

---

## Architecture

```
Yahoo Finance + FRED
        │
        ▼
Feature engineering (25 signals)
        │
        ▼
LightGBM + walk-forward + calibration
        │
        ├── SHAP explainability
        ├── Soft / hard gating engine
        ├── Gated vs ungated backtest
        └── Moving-block bootstrap + OOT tests
        │
        ▼
FastAPI  ──►  React dashboard (Vite + Tailwind + Recharts)
   │
   └── PostgreSQL (optional) + CSV cache
```

---

## Tech Stack

- **Research:** Python, pandas, NumPy/SciPy, LightGBM, SHAP
- **Validation:** expanding-window walk-forward, isotonic/Platt calibration, bootstrap significance
- **Serving:** FastAPI, React, Tailwind, Recharts
- **Infra:** Docker Compose, optional PostgreSQL, weekday `launchd` / shell daily refresh

---

## Project Structure

```
src/
  data/         # market data ingestion + validation
  features/     # vol term structure, credit, momentum, calendar
  models/       # LightGBM, walk-forward, calibration
  evaluation/   # backtest, gating engine, metrics, significance
  api/          # FastAPI + dashboard payloads
frontend/       # React dashboard
assets/         # README demo video
outputs/        # per-threshold predictions + gating summaries
data/model_outputs/   # wf predictions, SHAP, significance artifacts
scripts/        # refresh, metrics, schedulers
config/         # config.yaml
```

---

## Quick Start

```bash
git clone https://github.com/kyeongmin3256/tail-risk-gating.git
cd tail-risk-gating
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# optional: export FRED_API_KEY=...
python run_pipeline.py
python run_training.py
```

Dashboard (API + UI + Postgres):

```bash
docker compose up -d
cd frontend && npm install && npm run dev
# API: http://localhost:8000   UI: http://localhost:5173
```

Weekday model refresh (fetch → train → `wf_predictions.csv`):

```bash
./scripts/run_daily_refresh.sh
./scripts/setup_daily_refresh_launchd.sh   # macOS, default 06:00 weekdays
```

---

## Scope

- Research / paper-style evaluation on a **short-straddle proxy**, not live options execution.
- Metrics drift when the data panel is refreshed; cite the artifacts above for a given claim.
- Dashboard is a research monitor (probability, drivers, gated equity) — not a brokerage UI.

---

## License

MIT
