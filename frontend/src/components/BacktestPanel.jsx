import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

function StatCompare({ label, gated, ungated, format = 'pct', higherBetter = true }) {
  const formatVal = (v) => {
    switch (format) {
      case 'pct': return (v * 100).toFixed(1) + '%'
      case 'ratio': return v.toFixed(2)
      case 'days': return v.toLocaleString()
      default: return v
    }
  }

  const gatedBetter = higherBetter ? gated > ungated : gated < ungated

  return (
    <div className="py-3 border-b border-white/[0.04] last:border-0">
      <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider mb-2">{label}</p>
      <div className="flex gap-4">
        <div className="flex-1">
          <span className={`text-lg font-mono font-bold ${gatedBetter ? 'text-accent-cyan' : 'text-white/50'}`}>
            {formatVal(gated)}
          </span>
          {gatedBetter && <span className="text-[9px] text-accent-cyan ml-1.5">✓</span>}
        </div>
        <div className="flex-1 text-right">
          <span className={`text-lg font-mono font-bold ${!gatedBetter ? 'text-accent-cyan' : 'text-white/50'}`}>
            {formatVal(ungated)}
          </span>
          {!gatedBetter && <span className="text-[9px] text-accent-cyan ml-1.5">✓</span>}
        </div>
      </div>
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-700 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-[10px] font-mono text-white/40 mb-1">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-xs font-mono" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === 'number'
            ? (entry.dataKey.includes('gated') || entry.dataKey.includes('ungated')
              ? entry.value.toFixed(3)
              : entry.value.toFixed(3))
            : entry.value}
        </p>
      ))}
    </div>
  )
}

export default function BacktestPanel({ data }) {
  const [chart, setChart] = useState('equity')
  const { gated, ungated } = data.summary

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-display text-sm font-semibold text-white/60 uppercase tracking-wider">
            Backtest Results
          </h2>
          <p className="text-[10px] font-mono text-white/25 mt-1">
            Gated vs Ungated short-vol strategy · {ungated.tradingDays} trading days · {gated.daysGated} days gated
          </p>
        </div>
        <div className="flex bg-white/[0.04] rounded-lg p-0.5">
          {['equity', 'drawdown'].map((t) => (
            <button
              key={t}
              onClick={() => setChart(t)}
              className={`text-[11px] font-mono px-3 py-1 rounded-md transition-all ${
                chart === t
                  ? 'bg-white/10 text-white'
                  : 'text-white/30 hover:text-white/50'
              }`}
            >
              {t === 'equity' ? 'Equity Curve' : 'Drawdown'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Chart */}
        <div className="flex-1 min-w-0">
          <div className="h-[300px]">
            {chart === 'equity' ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.equityCurve}>
                  <defs>
                    <linearGradient id="gatedFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06d6d0" stopOpacity={0.12} />
                      <stop offset="100%" stopColor="#06d6d0" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="ungatedFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7a7d8e" stopOpacity={0.08} />
                      <stop offset="100%" stopColor="#7a7d8e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" interval={Math.floor(data.equityCurve.length / 6)} tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={(v) => v.toFixed(1) + 'x'} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="ungated" stroke="#7a7d8e" strokeWidth={1.5} fill="url(#ungatedFill)"
                    name="Ungated" strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="gated" stroke="#06d6d0" strokeWidth={2} fill="url(#gatedFill)"
                    name="Gated" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.drawdownSeries}>
                  <defs>
                    <linearGradient id="ddGatedFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06d6d0" stopOpacity={0} />
                      <stop offset="100%" stopColor="#06d6d0" stopOpacity={0.15} />
                    </linearGradient>
                    <linearGradient id="ddUngatedFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ff3b5c" stopOpacity={0} />
                      <stop offset="100%" stopColor="#ff3b5c" stopOpacity={0.15} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" interval={Math.floor(data.drawdownSeries.length / 6)} tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={(v) => (v * 100).toFixed(0) + '%'} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="ungated" stroke="#ff3b5c" strokeWidth={1.5} fill="url(#ddUngatedFill)"
                    name="Ungated" strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="gated" stroke="#06d6d0" strokeWidth={2} fill="url(#ddGatedFill)"
                    name="Gated" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Chart legend */}
          <div className="flex justify-center gap-6 mt-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-0.5 bg-accent-cyan rounded" />
              <span className="text-[10px] font-mono text-white/40">Gated (gate @ 15%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-5 h-0.5 bg-white/30 rounded" style={{ borderTop: '1px dashed rgba(255,255,255,0.3)' }} />
              <span className="text-[10px] font-mono text-white/40">Ungated</span>
            </div>
          </div>
        </div>

        {/* Stats sidebar */}
        <div className="lg:w-[260px] shrink-0">
          <div className="flex gap-4 pb-2 border-b border-white/[0.08]">
            <div className="flex-1">
              <span className="text-[10px] font-mono text-accent-cyan uppercase tracking-wider font-semibold">Gated</span>
            </div>
            <div className="flex-1 text-right">
              <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider font-semibold">Ungated</span>
            </div>
          </div>

          <StatCompare label="Total Return" gated={gated.totalReturn - 1} ungated={ungated.totalReturn - 1} />
          <StatCompare label="Ann. Return" gated={gated.annualizedReturn} ungated={ungated.annualizedReturn} />
          <StatCompare label="Sharpe Ratio" gated={gated.sharpe} ungated={ungated.sharpe} format="ratio" />
          <StatCompare label="Max Drawdown" gated={gated.maxDrawdown} ungated={ungated.maxDrawdown} higherBetter={false} />
          <StatCompare label="Calmar Ratio" gated={gated.calmar} ungated={ungated.calmar} format="ratio" />
        </div>
      </div>
    </div>
  )
}
