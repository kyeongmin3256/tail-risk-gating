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

Model pipeline, significance testing, FastAPI serving, and React dashboard are complete. Next phase: soft-gating policy tuning and cloud deployment.
