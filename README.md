# TailCast

TailCast is an ML-driven **tail-risk gating system** for short-volatility strategies.

It predicts the conditional probability of extreme downside events in SPY and turns that probability into explicit trading actions (trade, reduce, or skip) to improve risk-adjusted performance.

## Objective

Short-vol strategies can produce stable carry most of the time, but are vulnerable to regime-shift drawdowns.
TailCast is designed to answer one question each day:

**"Should this strategy be traded today, given current tail-risk conditions?"**

## Core Results

<!-- METRICS:START -->
### Walk-forward gated vs Short Straddle B&H (-4% model bucket, hard @ 15%)

- Sharpe: `1.9444 -> 1.8055` (**-7.14%**)
- CVaR(95): `-0.0543 -> -0.0540` (**0.68% tail-risk reduction**)
- Gate activity: `86` low-exposure days

### Best full-sample profile (-2% bucket, soft @ 20%)

- Sharpe: `1.9444 -> 2.0273` (**+4.26%**)
- CVaR(95): `-0.0543 -> -0.0468` (**13.93% tail-risk reduction**)
- OOT soft gate (-2% @ 20%, last 756 days): Sharpe delta `+0.1852` · CVaR improvement `0.00611`
<!-- METRICS:END -->

### Walk-forward gated vs ungated (-4% model bucket)

- Sharpe: `0.8912 -> 0.9406` (**+5.55%**)
- CVaR(95): `-0.0105 -> -0.0101` (**4.16% tail-risk reduction**)
- Annual return: `5.79% -> 5.90%` (**+1.95%**)
- Gate activity: `days_scaled=83`, `days_in_cash=35`

### Significance diagnostics

TailCast includes moving-block bootstrap significance tests for Sharpe/CVaR deltas and threshold sweeps.

- Candidate configuration with strongest OOT profile: `threshold=2`, `soft gate=0.20`
- OOT Sharpe delta: `+0.1852`
- OOT CVaR improvement: `+0.00611`

Artifacts:

- `data/model_outputs/significance_sweep_t2_soft.csv`
- `data/model_outputs/significance_oot_t2_soft.csv`

## Architecture

```text
Yahoo Finance + FRED
        ↓
Phase 1: Data pipeline + feature engineering (25+ features)
        ↓
Phase 2: LightGBM + walk-forward + calibration + SHAP
        ↓
Phase 3: Gated vs ungated strategy evaluation + significance testing
        ↓
Phase 4: FastAPI + React/Tailwind dashboard
```

## System Components

- **Data**: Yahoo Finance + FRED ingestion with CSV cache and PostgreSQL persistence
- **Features**: volatility term structure, credit stress, momentum, calendar regime context
- **Model**: LightGBM classifier with class-imbalance handling
- **Validation**: expanding-window walk-forward retraining
- **Calibration**: isotonic / platt scaling for probability interpretability
- **Explainability**: SHAP-based global and daily risk drivers
- **Serving**: FastAPI endpoints delivering real dashboard payloads
- **Frontend**: React + Tailwind + Recharts, threshold-aware dashboard UX

## Repository Structure

```text
src/
├── data/          # Yahoo Finance + FRED ingestion
├── features/      # feature engineering
├── labels/        # target definition
├── models/        # LightGBM, walk-forward, calibration, SHAP
├── evaluation/    # backtesting + metrics
└── api/           # FastAPI endpoints

frontend/
└── src/components # RiskGauge, ModelMetrics, ShapChart, BacktestPanel
```

## Quick Start

```bash
git clone https://github.com/kyeongmin3256/tail-risk-gating.git
cd tail-risk-gating
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Optional FRED key:

```bash
export FRED_API_KEY=your_key_here
```

Run pipeline and training:

```bash
python run_pipeline.py
python run_training.py
```

PostgreSQL (optional, dual-write with CSV cache):

```bash
docker compose up -d db
python3 scripts/init_db.py
python3 scripts/migrate_csv_to_db.py      # import existing data/raw CSVs
python3 run_pipeline.py --use-cache     # load from PostgreSQL when available
python3 run_pipeline.py                 # fetch fresh data into CSV + PostgreSQL
```

Run multi-threshold training:

```bash
python run_multi_threshold.py
```

Run significance analysis:

```bash
python run_significance.py --sweep --compare-modes --thresholds 2 4 6 8 --gate-thresholds 0.10 0.15 0.20 0.25
```

Run API:

```bash
uvicorn src.api.main:app --reload --port 8000
```

Run frontend:

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## License

MIT
