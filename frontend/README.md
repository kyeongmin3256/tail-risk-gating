# TailCast Dashboard

React + Tailwind frontend for the TailCast tail risk estimation system.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Proxies `/api/*` to `http://localhost:8000` (FastAPI backend).

## Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Header.jsx          # Logo + live indicator
│   │   ├── RiskGauge.jsx       # Hero: gauge + today's risk drivers
│   │   ├── ModelMetrics.jsx    # ROC curve, walk-forward folds, metrics
│   │   ├── ShapChart.jsx       # SHAP feature importance bars
│   │   └── BacktestPanel.jsx   # Equity curve, drawdown, gated vs ungated
│   ├── data/
│   │   └── mockData.js         # ← Replace with API calls
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Connecting to FastAPI

The mock data in `src/data/mockData.js` mirrors expected API responses.
Replace imports with fetch calls to your FastAPI backend:

```js
// Before (mock):
import { todayRisk } from '../data/mockData'

// After (API):
const [todayRisk, setTodayRisk] = useState(null)
useEffect(() => {
  fetch('/api/predict').then(r => r.json()).then(setTodayRisk)
}, [])
```

Expected endpoints:
- `GET /api/predict` → today's risk probability + drivers
- `GET /api/metrics` → model performance metrics
- `GET /api/shap` → SHAP feature importance values
- `GET /api/backtest` → backtest results (gated vs ungated)

## Build for Production

```bash
npm run build    # outputs to dist/
npm run preview  # preview production build
```
