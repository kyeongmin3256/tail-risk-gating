# Conditional Tail Risk Probability Estimation for Short-Volatility Strategies

A calibrated probabilistic model that estimates the likelihood of extreme losses under current market conditions, enabling traders to make informed risk-gating decisions based on their own loss tolerance.

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/YOUR_USERNAME/tail-risk-gating.git
cd tail-risk-gating

python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

pip install -r requirements.txt
```

### 2. (Optional) Set FRED API key

Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html

```bash
export FRED_API_KEY=your_key_here
```

Without an API key, the system falls back to FRED's public CSV endpoint.

### 3. Run the data pipeline

```bash
# Fetch data and build features
python run_pipeline.py

# Use cached data on subsequent runs
python run_pipeline.py --use-cache

# Custom parameters
python run_pipeline.py --threshold -0.10 --horizon 10
```

### 4. Run tests

```bash
pytest tests/ -v
```

### 5. (Optional) Start Postgres for data storage

```bash
docker-compose up -d
```

## Project Structure

```
src/
├── data/          # Data fetching (Yahoo Finance, FRED)
├── features/      # Feature engineering (volatility, market structure, momentum, calendar)
├── labels/        # Strategy definition and label computation
├── models/        # ML models and calibration (Phase 2)
├── evaluation/    # Backtesting and evaluation (Phase 3)
├── api/           # FastAPI service (Phase 4)
└── dashboard/     # Streamlit dashboard (Phase 4)
```

## Data Sources

All data is free and publicly available:
- **Yahoo Finance**: SPY, VIX, VVIX, SKEW, VIX9D, VIX3M, HYG, IEF, UUP
- **FRED**: 2Y and 10Y Treasury yields

## How It Works

1. **Features** capture market stress signals: volatility levels, term structure, credit spreads, yield curve, momentum
2. **Labels** define "bad outcomes": periods where a short straddle on SPY would lose more than the trader's threshold
3. **Model** estimates P(loss > threshold | current market conditions) as a calibrated probability
4. **Evaluation** compares gated vs. ungated strategy performance across drawdown, CVaR, and premium sacrificed

## License

MIT
