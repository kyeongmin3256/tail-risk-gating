import { useMemo, useState, useEffect } from 'react'
import Header from './components/Header'
import OverviewStrip from './components/OverviewStrip'
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
      <div className="mx-auto max-w-6xl px-6 py-16 font-mono text-sm text-muted">
        No dashboard data available.
      </div>
    )
  }

  const blendHint = data.bracket?.w > 0
    ? `Blending −${data.bracket.lower}% and −${data.bracket.upper}% models`
    : null

  const policy = data.backtestResults?.gatingPolicy ?? {
    gateThreshold: 0.15,
    label: 'Hard Gate @ 15%',
  }

  return (
    <div className="min-h-screen bg-paper">
      <div className="mx-auto max-w-6xl px-6 py-8 md:py-10">
        <Header status={apiError ? 'Mock Data' : 'Operational'} statusKind={apiError ? 'warn' : 'ok'} />

        {loading && (
          <p className="mt-4 font-mono text-xs text-muted">Loading dashboard data from API…</p>
        )}
        {!loading && apiError && (
          <p className="mt-4 font-mono text-xs text-warn">{apiError}</p>
        )}

        <OverviewStrip
          asOf={data.todayRisk.date}
          probability={data.todayRisk.probability}
          gateThreshold={policy.gateThreshold}
          lossTolerance={lossTolerance}
          policyLabel={policy.label}
        />

        <section className="mt-5 border border-line bg-[#EDEAE3]/30 p-4 sm:p-5">
          <RiskGauge
            data={data.todayRisk}
            gatingPolicy={policy}
            lossTolerance={lossTolerance}
            onLossToleranceChange={setLossTolerance}
            thresholds={thresholds}
            blendHint={blendHint}
          />
        </section>

        <section className="mt-5 border border-line bg-[#EDEAE3]/30 p-4 sm:p-5 grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ModelMetrics data={data.modelMetrics} />
          <ShapChart data={data.shapValues} />
        </section>

        <section className="mt-5 border border-line bg-[#EDEAE3]/30 p-4 sm:p-5">
          <BacktestPanel data={data.backtestResults} />
        </section>

        <footer className="mt-10 border-t border-line pt-4 font-mono text-[10px] uppercase tracking-label text-muted">
          TailCast · Walk-Forward LightGBM · −{lossTolerance.toFixed(1)}% loss tolerance
          {blendHint ? ` · ${blendHint}` : ''} · Data through {data.todayRisk.date}
        </footer>
      </div>
    </div>
  )
}
