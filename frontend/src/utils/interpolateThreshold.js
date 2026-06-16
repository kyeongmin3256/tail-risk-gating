function lerp(a, b, w) {
  return a * (1 - w) + b * w
}

function getBracket(thresholds, value) {
  const sorted = [...thresholds].sort((a, b) => a - b)
  const t = Math.min(Math.max(value, sorted[0]), sorted[sorted.length - 1])

  let lower = sorted[0]
  let upper = sorted[sorted.length - 1]
  for (let i = 0; i < sorted.length - 1; i++) {
    if (t >= sorted[i] && t <= sorted[i + 1]) {
      lower = sorted[i]
      upper = sorted[i + 1]
      break
    }
  }

  const w = upper === lower ? 0 : (t - lower) / (upper - lower)
  return { lower, upper, w, value: t }
}

function blendSummary(a, b, w) {
  const keys = ['totalReturn', 'annualizedReturn', 'sharpe', 'maxDrawdown', 'calmar', 'tradingDays', 'daysGated']
  const out = {}
  for (const key of keys) {
    out[key] = Math.round(lerp(a[key], b[key], w) * 10000) / 10000
  }
  return out
}

function blendSeries(seriesA, seriesB, w, keys) {
  const len = Math.min(seriesA.length, seriesB.length)
  const out = []
  for (let i = 0; i < len; i++) {
    const row = { date: seriesA[i].date }
    for (const key of keys) {
      row[key] = lerp(seriesA[i][key], seriesB[i][key], w)
    }
    out.push(row)
  }
  return out
}

function blendTopDrivers(a, b, w) {
  const byFeature = new Map(b.map((d) => [d.feature, d]))
  return a.map((drv) => {
    const other = byFeature.get(drv.feature)
    if (!other) return drv
    return {
      ...drv,
      shapValue: lerp(drv.shapValue, other.shapValue, w),
      direction: w < 0.5 ? drv.direction : other.direction,
    }
  })
}

function blendShapValues(a, b, w) {
  const byFeature = new Map(b.map((d) => [d.rawFeature, d]))
  return a.map((row) => {
    const other = byFeature.get(row.rawFeature)
    if (!other) return row
    return {
      ...row,
      importance: lerp(row.importance, other.importance, w),
      direction: w < 0.5 ? row.direction : other.direction,
    }
  })
}

function blendGatingPolicy(a, b, w, lossTolerance) {
  const gateThreshold = lerp(a.gateThreshold, b.gateThreshold, w)
  const mode = w < 0.5 ? a.mode : b.mode
  const modeLabel = mode === 'soft' ? 'Soft' : 'Hard'
  const exact = w === 0

  return {
    mode,
    gateThreshold,
    benchmarkLabel: a.benchmarkLabel ?? b.benchmarkLabel,
    label: exact
      ? a.label
      : w === 1
        ? b.label
        : `${modeLabel} Gate @ ${(gateThreshold * 100).toFixed(0)}% · −${lossTolerance.toFixed(1)}% loss`,
  }
}

function blendModelMetrics(a, b, w) {
  const rocLen = Math.min(a.rocCurve?.length ?? 0, b.rocCurve?.length ?? 0)
  const rocCurve = []
  for (let i = 0; i < rocLen; i++) {
    rocCurve.push({
      fpr: lerp(a.rocCurve[i].fpr, b.rocCurve[i].fpr, w),
      tpr: lerp(a.rocCurve[i].tpr, b.rocCurve[i].tpr, w),
    })
  }

  const foldLen = Math.min(a.walkForwardFolds?.length ?? 0, b.walkForwardFolds?.length ?? 0)
  const walkForwardFolds = []
  for (let i = 0; i < foldLen; i++) {
    const fa = a.walkForwardFolds[i]
    const fb = b.walkForwardFolds[i]
    walkForwardFolds.push({
      ...fa,
      auc: fa.auc != null && fb.auc != null ? lerp(fa.auc, fb.auc, w) : fa.auc,
    })
  }

  const calLen = Math.min(
    a.calibration?.predicted?.length ?? 0,
    b.calibration?.predicted?.length ?? 0,
  )
  const calibration = {
    predicted: [],
    observed: [],
  }
  for (let i = 0; i < calLen; i++) {
    calibration.predicted.push(lerp(a.calibration.predicted[i], b.calibration.predicted[i], w))
    calibration.observed.push(lerp(a.calibration.observed[i], b.calibration.observed[i], w))
  }

  return {
    ...a,
    rocAuc: lerp(a.rocAuc, b.rocAuc, w),
    avgPrecision: lerp(a.avgPrecision, b.avgPrecision, w),
    brierScore: lerp(a.brierScore, b.brierScore, w),
    benchmarks: a.benchmarks,
    rocCurve,
    walkForwardFolds,
    calibration,
  }
}

function blendBacktest(a, b, w, lossTolerance) {
  const gated = blendSummary(a.summary.gated, b.summary.gated, w)
  const baselineA = a.summary.baseline ?? a.summary.ungated
  const baselineB = b.summary.baseline ?? b.summary.ungated
  const baseline = blendSummary(baselineA, baselineB, w)

  return {
    gatingPolicy: blendGatingPolicy(a.gatingPolicy, b.gatingPolicy, w, lossTolerance),
    summary: { gated, baseline, ungated: baseline },
    equityCurve: blendSeries(a.equityCurve, b.equityCurve, w, ['gated', 'ungated']),
    drawdownSeries: blendSeries(a.drawdownSeries, b.drawdownSeries, w, ['gated', 'ungated']),
  }
}

export function interpolateDashboardData(source, thresholds, lossTolerance) {
  const available = thresholds.filter((t) => source[String(t)])
  if (!available.length) return null

  const { lower, upper, w, value } = getBracket(available, lossTolerance)
  const lowData = source[String(lower)]
  if (lower === upper || w === 0) {
    return {
      ...lowData,
      lossTolerance: value,
      bracket: { lower, upper, w: 0 },
    }
  }

  const highData = source[String(upper)]
  return {
    lossTolerance: value,
    bracket: { lower, upper, w },
    todayRisk: {
      ...lowData.todayRisk,
      probability: lerp(lowData.todayRisk.probability, highData.todayRisk.probability, w),
      topDrivers: blendTopDrivers(lowData.todayRisk.topDrivers, highData.todayRisk.topDrivers, w),
    },
    modelMetrics: blendModelMetrics(lowData.modelMetrics, highData.modelMetrics, w),
    shapValues: blendShapValues(lowData.shapValues, highData.shapValues, w),
    backtestResults: blendBacktest(
      lowData.backtestResults,
      highData.backtestResults,
      w,
      value,
    ),
  }
}
