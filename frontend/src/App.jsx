import React, { useMemo, useState, useEffect } from 'react'
import Header from './components/Header'
import RiskGauge from './components/RiskGauge'
import ModelMetrics from './components/ModelMetrics'
import ShapChart from './components/ShapChart'
import BacktestPanel from './components/BacktestPanel'
import { THRESHOLDS, dataByThreshold } from './data/mockData'
import { interpolateDashboardData } from './utils/interpolateThreshold'

export default function App() {
  const [lossTolerance, setLossTolerance] = useState(4)
  const [thresholds, setThresholds] = useState(THRESHOLDS)
  const [apiDataByThreshold, setApiDataByThreshold] = useState(null)
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState('')

  useEffect(() => {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    fetch(`${base}/api/dashboard/data`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((json) => {
        if (json?.thresholds && json?.dataByThreshold) {
          setThresholds(json.thresholds)
          setApiDataByThreshold(json.dataByThreshold)
        } else {
          throw new Error('Invalid API payload')
        }
      })
      .catch((err) => {
        setApiError(`API unavailable (${err.message}), using local mock data`)
      })
      .finally(() => setLoading(false))
  }, [])

  const source = apiDataByThreshold || dataByThreshold
  const data = useMemo(
    () => interpolateDashboardData(source, thresholds, lossTolerance),
    [source, thresholds, lossTolerance],
  )

  if (!data) {
    return (
      <div className="min-h-screen bg-surface-900 noise-overlay relative">
        <div className="relative z-10 max-w-[1440px] mx-auto px-6 py-6">
          <Header />
          <section className="mt-6">
            <div className="card px-4 py-3 text-sm font-mono text-white/50">
              No dashboard data available.
            </div>
          </section>
        </div>
      </div>
    )
  }

  const blendHint = data.bracket?.w > 0
    ? `Blending −${data.bracket.lower}% and −${data.bracket.upper}% models`
    : null

  return (
    <div className="min-h-screen bg-surface-900 noise-overlay relative">
      <div className="relative z-10 max-w-[1440px] mx-auto px-6 py-6">
        <Header />

        {loading && (
          <section className="mt-4">
            <div className="card px-4 py-3 text-xs font-mono text-white/40">
              Loading dashboard data from API...
            </div>
          </section>
        )}
        {!loading && apiError && (
          <section className="mt-4">
            <div className="card px-4 py-3 text-xs font-mono text-amber-300/80">
              {apiError}
            </div>
          </section>
        )}

        <section className="mt-6">
          <RiskGauge
            data={data.todayRisk}
            gatingPolicy={data.backtestResults?.gatingPolicy}
            lossTolerance={lossTolerance}
            onLossToleranceChange={setLossTolerance}
            thresholds={thresholds}
            blendHint={blendHint}
          />
        </section>

        <section className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ModelMetrics data={data.modelMetrics} />
          <ShapChart data={data.shapValues} />
        </section>

        <section className="mt-6 mb-12">
          <BacktestPanel data={data.backtestResults} />
        </section>

        <footer className="border-t border-white/5 py-6 text-center">
          <p className="text-sm text-white/20 font-mono">
            TailCast v2.0 · Walk-Forward LightGBM · −{lossTolerance.toFixed(1)}% loss tolerance
            {blendHint ? ` · ${blendHint}` : ''} · Data through {data.todayRisk.date}
          </p>
        </footer>
      </div>
    </div>
  )
}
