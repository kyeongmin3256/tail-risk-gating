import React from 'react'
import Header from './components/Header'
import RiskGauge from './components/RiskGauge'
import ModelMetrics from './components/ModelMetrics'
import ShapChart from './components/ShapChart'
import BacktestPanel from './components/BacktestPanel'

export default function App() {
  return (
    <div className="min-h-screen bg-surface-900 noise-overlay relative">
      <div className="relative z-10 max-w-[1440px] mx-auto px-6 py-6">
        <Header />

        {/* Hero: Today's Risk */}
        <section className="mt-6">
          <RiskGauge />
        </section>

        {/* Two-column: Model Metrics + SHAP */}
        <section className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ModelMetrics />
          <ShapChart />
        </section>

        {/* Full-width: Backtest */}
        <section className="mt-6 mb-12">
          <BacktestPanel />
        </section>

        {/* Footer */}
        <footer className="border-t border-white/5 py-6 text-center">
          <p className="text-sm text-white/20 font-mono">
            TailCast v2.0 · Walk-Forward LightGBM · Data through 2026-03-14
          </p>
        </footer>
      </div>
    </div>
  )
}
