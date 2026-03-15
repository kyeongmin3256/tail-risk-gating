// Mock data matching TailCast Phase 2 model outputs.
// Replace with FastAPI calls in production:
//   GET /api/predict        → todayRisk
//   GET /api/metrics        → modelMetrics
//   GET /api/shap           → shapValues
//   GET /api/backtest       → backtestResults

export const todayRisk = {
  date: '2026-03-15',
  probability: 0.083,
  threshold: 0.175,
  signal: 'SAFE',  // 'SAFE' | 'CAUTION' | 'DANGER'
  topDrivers: [
    { feature: 'vix_term_slope', value: -0.12, direction: 'risk_increasing', description: 'VIX term structure inverted' },
    { feature: 'vix_level', value: 18.4, direction: 'neutral', description: 'VIX at moderate level' },
    { feature: 'vvix_level', value: 92.3, direction: 'neutral', description: 'VVIX within normal range' },
    { feature: 'skew_index', value: 138.5, direction: 'risk_increasing', description: 'Elevated tail risk pricing' },
    { feature: 'spy_momentum_5d', value: -0.018, direction: 'neutral', description: 'Slight negative momentum' },
  ],
  modelInfo: {
    lastTrained: '2026-03-14',
    dataThrough: '2026-03-14',
    windowSize: '756+ trading days',
  },
};

export const modelMetrics = {
  rocAuc: 0.74,
  avgPrecision: 0.20,
  brierScore: 0.058,
  calibration: {
    predicted: [0.02, 0.05, 0.10, 0.15, 0.25, 0.40],
    observed:  [0.01, 0.04, 0.08, 0.16, 0.22, 0.38],
  },
  rocCurve: [
    { fpr: 0.0, tpr: 0.0 },
    { fpr: 0.05, tpr: 0.28 },
    { fpr: 0.10, tpr: 0.42 },
    { fpr: 0.15, tpr: 0.52 },
    { fpr: 0.20, tpr: 0.60 },
    { fpr: 0.30, tpr: 0.70 },
    { fpr: 0.40, tpr: 0.78 },
    { fpr: 0.50, tpr: 0.84 },
    { fpr: 0.60, tpr: 0.89 },
    { fpr: 0.70, tpr: 0.93 },
    { fpr: 0.80, tpr: 0.96 },
    { fpr: 0.90, tpr: 0.98 },
    { fpr: 1.0, tpr: 1.0 },
  ],
  walkForwardFolds: [
    { fold: 1, period: '2014–2016', auc: 0.71, samples: 504, positives: 33 },
    { fold: 2, period: '2016–2018', auc: 0.73, samples: 504, positives: 31 },
    { fold: 3, period: '2018–2020', auc: 0.78, samples: 504, positives: 42 },
    { fold: 4, period: '2020–2022', auc: 0.76, samples: 504, positives: 38 },
    { fold: 5, period: '2022–2024', auc: 0.72, samples: 504, positives: 29 },
    { fold: 6, period: '2024–2026', auc: 0.70, samples: 315, positives: 18 },
  ],
};

export const shapValues = [
  { feature: 'VIX Term Slope', importance: 0.142, direction: 'negative' },
  { feature: 'VIX Level', importance: 0.118, direction: 'positive' },
  { feature: 'VVIX', importance: 0.097, direction: 'positive' },
  { feature: 'SKEW Index', importance: 0.089, direction: 'positive' },
  { feature: 'SPY 5d Momentum', importance: 0.074, direction: 'negative' },
  { feature: 'VIX9D/VIX Ratio', importance: 0.063, direction: 'positive' },
  { feature: 'HYG Spread', importance: 0.058, direction: 'positive' },
  { feature: 'VIX 20d Realized', importance: 0.052, direction: 'positive' },
  { feature: 'SPY 20d Volatility', importance: 0.048, direction: 'positive' },
  { feature: 'UUP Momentum', importance: 0.041, direction: 'positive' },
  { feature: 'VIX3M/VIX Ratio', importance: 0.038, direction: 'positive' },
  { feature: 'Day of Week', importance: 0.029, direction: 'mixed' },
  { feature: 'IEF Momentum', importance: 0.025, direction: 'negative' },
  { feature: 'Month Effect', importance: 0.022, direction: 'mixed' },
  { feature: 'SPY Gap', importance: 0.019, direction: 'negative' },
];

export const backtestResults = {
  summary: {
    gated: {
      totalReturn: 1.87,
      annualizedReturn: 0.112,
      sharpe: 1.24,
      maxDrawdown: -0.148,
      calmar: 0.757,
      winRate: 0.584,
      tradingDays: 2835,
      daysGated: 412,
    },
    ungated: {
      totalReturn: 1.62,
      annualizedReturn: 0.098,
      sharpe: 0.91,
      maxDrawdown: -0.284,
      calmar: 0.345,
      winRate: 0.548,
      tradingDays: 2835,
      daysGated: 0,
    },
  },
  // Cumulative return series (sampled monthly for chart)
  equityCurve: [
    { date: '2014-01', gated: 1.00, ungated: 1.00 },
    { date: '2014-07', gated: 1.05, ungated: 1.04 },
    { date: '2015-01', gated: 1.11, ungated: 1.08 },
    { date: '2015-07', gated: 1.13, ungated: 1.06 },
    { date: '2016-01', gated: 1.09, ungated: 1.01 },
    { date: '2016-07', gated: 1.18, ungated: 1.12 },
    { date: '2017-01', gated: 1.25, ungated: 1.19 },
    { date: '2017-07', gated: 1.34, ungated: 1.28 },
    { date: '2018-01', gated: 1.40, ungated: 1.35 },
    { date: '2018-07', gated: 1.38, ungated: 1.24 },
    { date: '2019-01', gated: 1.32, ungated: 1.15 },
    { date: '2019-07', gated: 1.45, ungated: 1.32 },
    { date: '2020-01', gated: 1.52, ungated: 1.40 },
    { date: '2020-04', gated: 1.48, ungated: 1.10 },
    { date: '2020-07', gated: 1.55, ungated: 1.28 },
    { date: '2021-01', gated: 1.68, ungated: 1.45 },
    { date: '2021-07', gated: 1.75, ungated: 1.52 },
    { date: '2022-01', gated: 1.80, ungated: 1.58 },
    { date: '2022-07', gated: 1.72, ungated: 1.38 },
    { date: '2023-01', gated: 1.78, ungated: 1.42 },
    { date: '2023-07', gated: 1.85, ungated: 1.50 },
    { date: '2024-01', gated: 1.90, ungated: 1.55 },
    { date: '2024-07', gated: 1.95, ungated: 1.60 },
    { date: '2025-01', gated: 1.92, ungated: 1.54 },
    { date: '2025-07', gated: 1.98, ungated: 1.58 },
    { date: '2026-01', gated: 1.87, ungated: 1.62 },
  ],
  drawdownSeries: [
    { date: '2014-01', gated: 0, ungated: 0 },
    { date: '2015-07', gated: -0.02, ungated: -0.04 },
    { date: '2016-01', gated: -0.05, ungated: -0.10 },
    { date: '2018-07', gated: -0.06, ungated: -0.12 },
    { date: '2019-01', gated: -0.08, ungated: -0.18 },
    { date: '2020-04', gated: -0.148, ungated: -0.284 },
    { date: '2020-07', gated: -0.04, ungated: -0.14 },
    { date: '2022-07', gated: -0.07, ungated: -0.16 },
    { date: '2023-01', gated: -0.03, ungated: -0.10 },
    { date: '2025-01', gated: -0.05, ungated: -0.08 },
    { date: '2026-01', gated: -0.06, ungated: -0.05 },
  ],
};
