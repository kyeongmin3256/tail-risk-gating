# TailCast: Conditional Tail-Risk Forecasting for Short-Vol Strategies

TailCast is a quantitative ML system that estimates daily conditional tail-risk probabilities and converts them into deterministic risk-gating decisions for short-volatility strategies.

## What TailCast Does

TailCast forecasts:

- `P(extreme_loss | current market state)`

and uses simple policy rules:

- elevated risk -> reduce exposure
- extreme risk -> move to cash

The objective is to improve risk-adjusted performance and reduce left-tail damage during regime stress.

## Current Scope

- Python + PostgreSQL data pipeline with long-history market data ingestion
- Feature engineering focused on volatility, credit stress, momentum, and calendar context
- LightGBM classifier for tail-event likelihood prediction
- Probability calibration (isotonic or Platt/scikit-learn logistic)
- Walk-forward validation/backtesting with out-of-sample predictions
- Explainability via SHAP
- FastAPI service and React/Tailwind frontend

## Backtest Snapshot

Latest gating run (walk-forward, calibrated probabilities):

- Sharpe: `0.8912 -> 0.9406` (**+5.55%**)
- CVaR(95): `-0.0105 -> -0.0101` (**4.16% risk reduction**)
- Annual return: `5.79% -> 5.90%` (**+1.95%**)
- Max drawdown: `-0.1312 -> -0.1312` (effectively unchanged)
- Gate activity: `days_scaled=83`, `days_in_cash=35`

Notes:

- These numbers summarize gated vs ungated strategy outcomes under the current threshold setup.
- The benchmark in current reports is `benchmark_60_40`.

## Quick Start

### 1) Environment setup

```bash
git clone https://github.com/kyeongmin3256/tail-risk-gating.git
cd tail-risk-gating

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Optional: FRED API key

Get a free key: https://fred.stlouisfed.org/docs/api/api_key.html

```bash
export FRED_API_KEY=your_key_here
```

### 3) Build dataset and labels (Phase 1)

```bash
python run_pipeline.py
```

Useful options:

```bash
python run_pipeline.py --use-cache
python run_pipeline.py --threshold -0.10 --horizon 10
```

### 4) Train and evaluate (Phase 2)

```bash
python run_training.py
```

### 5) Optional: model pipeline variant

```bash
python run_model.py --skip-shap
```

### 6) Run tests

```bash
pytest tests/ -v
```

### 7) Optional: start Postgres

```bash
docker-compose up -d
```

## Project Structure

```text
src/
├── data/          # Data ingestion (Yahoo Finance, FRED)
├── features/      # Volatility, market structure, momentum, calendar features
├── labels/        # Strategy proxy + binary/continuous target creation
├── models/        # LightGBM training, calibration, walk-forward engine, SHAP
├── evaluation/    # Metrics and backtesting logic
├── api/           # FastAPI service
└── dashboard/     # Frontend integration hooks
```

## Data Sources

All sources are publicly accessible:

- Yahoo Finance: SPY, VIX, VVIX, SKEW, VIX9D, VIX3M, HYG, IEF, UUP
- FRED: 2Y and 10Y Treasury yields

## Method Summary

1. Build market-state features from daily cross-asset and macro signals.
2. Define tail outcomes from forward strategy loss proxy.
3. Train classifier to estimate tail-event probability.
4. Calibrate probabilities for threshold interpretability.
5. Run expanding-window walk-forward tests.
6. Compare gated vs ungated outcomes on return and tail-risk metrics.

## Next Improvements

- Add result visuals to repository root:
  - cumulative equity (gated vs ungated)
  - gating activation timeline
  - probability calibration curve
- Add explicit short-straddle buy-and-hold benchmark line to summary reports.

## License

MIT
