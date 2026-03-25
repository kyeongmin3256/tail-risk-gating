import React, { useState } from 'react'
import Header from './components/Header'
import RiskGauge from './components/RiskGauge'
import ModelMetrics from './components/ModelMetrics'
import ShapChart from './components/ShapChart'
import BacktestPanel from './components/BacktestPanel'
import { THRESHOLDS, dataByThreshold } from './data/mockData'

export default function App() {
  const [modelThreshold, setModelThreshold] = useState(4)
  const data = dataByThreshold[String(modelThreshold)]

  return (
    <div className="min-h-screen bg-surface-900 noise-overlay relative">
      <div className="relative z-10 max-w-[1440px] mx-auto px-6 py-6">
        <Header />

        {/* Model Threshold Selector */}
        <section className="mt-4">
          <div className="card px-6 py-4 flex items-center gap-6">
            <div>
              <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider mb-1">
                Loss Tolerance Model
              </p>
              <p className="text-[10px] font-mono text-white/20 leading-relaxed">
                Select the max loss you can tolerate — the corresponding model's predictions are shown throughout.
              </p>
            </div>
            <div className="flex gap-2 ml-auto">
              {THRESHOLDS.map((t) => (
                <button
                  key={t}
                  onClick={() => setModelThreshold(t)}
                  className={`px-4 py-2 rounded-lg text-xs font-mono font-semibold transition-all border ${
                    modelThreshold === t
                      ? 'bg-accent-cyan/10 border-accent-cyan/40 text-accent-cyan'
                      : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/60 hover:border-white/20'
                  }`}
                >
                  -{t}%
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Hero: Today's Risk */}
        <section className="mt-6">
          <RiskGauge data={data.todayRisk} />
        </section>

        {/* Two-column: Model Metrics + SHAP */}
        <section className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ModelMetrics data={data.modelMetrics} />
          <ShapChart data={data.shapValues} />
        </section>

        {/* Full-width: Backtest */}
        <section className="mt-6 mb-12">
          <BacktestPanel data={data.backtestResults} />
        </section>

        {/* Footer */}
        <footer className="border-t border-white/5 py-6 text-center">
          <p className="text-sm text-white/20 font-mono">
            TailCast v2.0 · Walk-Forward LightGBM · -{modelThreshold}% Loss Tolerance Model · Data through {data.todayRisk.date}
          </p>
        </footer>
      </div>
    </div>
  )
}
