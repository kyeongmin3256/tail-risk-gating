import { useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

const INK = '#1F4B6E'
const BENCH = '#8B8680'
const LINE = '#D9D4C8'
const TICK = { fontSize: 9, fill: '#5C5A55', fontFamily: 'IBM Plex Mono' }
const TOOLTIP_STYLE = {
  background: '#F3F1EC',
  border: '1px solid #D9D4C8',
  fontFamily: 'IBM Plex Mono',
  fontSize: 11,
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border px-3 py-1 font-mono text-[11px] uppercase tracking-label transition ${
        active
          ? 'border-ink text-ink bg-ink/5'
          : 'border-line text-muted hover:border-muted hover:text-ink-deep'
      }`}
    >
      {children}
    </button>
  )
}

function StatCompare({ label, gated, baseline, format = 'pct', higherBetter = true }) {
  const formatVal = (v) => {
    switch (format) {
      case 'pct': return (v * 100).toFixed(1) + '%'
      case 'ratio': return v.toFixed(2)
      case 'days': return v.toLocaleString()
      default: return v
    }
  }

  const gatedBetter = higherBetter ? gated > baseline : gated < baseline

  return (
    <div className="py-3 border-b border-line/80 last:border-0">
      <p className="text-[10px] font-mono uppercase tracking-label text-muted mb-2">{label}</p>
      <div className="flex gap-4">
        <div className="flex-1">
          <span className={`font-mono text-lg font-medium ${gatedBetter ? 'text-ink' : 'text-muted'}`}>
            {formatVal(gated)}
          </span>
        </div>
        <div className="flex-1 text-right">
          <span className={`font-mono text-lg font-medium ${!gatedBetter ? 'text-ink' : 'text-muted'}`}>
            {formatVal(baseline)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function BacktestPanel({ data }) {
  const [chart, setChart] = useState('equity')
  const { gated, baseline, ungated } = data.summary
  const bench = baseline ?? ungated
  const policy = data.gatingPolicy ?? {
    label: 'Hard Gate @ 15%',
    benchmarkLabel: 'Short Straddle B&H',
    mode: 'hard',
    gateThreshold: 0.15,
  }

  const chartData = chart === 'equity' ? data.equityCurve : data.drawdownSeries

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5 gap-4">
        <div>
          <h3 className="font-display text-base font-semibold text-ink">Backtest Results</h3>
          <p className="text-[10px] font-mono text-muted mt-1">
            {policy.label} vs {policy.benchmarkLabel} · {bench.tradingDays} trading days · {gated.daysGated} low-exposure days
          </p>
        </div>
        <div className="flex gap-2">
          <TabButton active={chart === 'equity'} onClick={() => setChart('equity')}>Equity Curve</TabButton>
          <TabButton active={chart === 'drawdown'} onClick={() => setChart('drawdown')}>Drawdown</TabButton>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1 min-w-0">
          <div className="h-[300px] border border-line bg-[#EDEAE3]/30 px-1 py-2 sm:px-2">
            <ResponsiveContainer width="100%" height="100%">
              {chart === 'equity' ? (
                <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={LINE} strokeDasharray="3 6" vertical={false} />
                  <XAxis
                    dataKey="date"
                    interval={Math.floor(chartData.length / 6)}
                    tick={TICK}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(v) => v.toFixed(1) + 'x'}
                    tick={TICK}
                    width={40}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Line
                    type="monotone"
                    dataKey="ungated"
                    stroke={BENCH}
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                    name={policy.benchmarkLabel}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="gated"
                    stroke={INK}
                    strokeWidth={1.75}
                    dot={false}
                    name={policy.label}
                    isAnimationActive={false}
                  />
                </LineChart>
              ) : (
                <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={LINE} strokeDasharray="3 6" vertical={false} />
                  <XAxis
                    dataKey="date"
                    interval={Math.floor(chartData.length / 6)}
                    tick={TICK}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(v) => (v * 100).toFixed(0) + '%'}
                    tick={TICK}
                    width={40}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Area
                    type="monotone"
                    dataKey="ungated"
                    stroke="#9B3A3A"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    fill="rgba(155, 58, 58, 0.06)"
                    name={policy.benchmarkLabel}
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="gated"
                    stroke={INK}
                    strokeWidth={1.75}
                    fill="rgba(31, 75, 110, 0.06)"
                    name={policy.label}
                    isAnimationActive={false}
                  />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </div>

          <div className="flex justify-center gap-8 mt-4">
            <div className="flex items-center gap-2">
              <span className="w-5 h-0.5 bg-ink" />
              <span className="text-[10px] font-mono text-muted">{policy.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-5 border-t border-dashed border-muted" />
              <span className="text-[10px] font-mono text-muted">{policy.benchmarkLabel}</span>
            </div>
          </div>
        </div>

        <div className="lg:w-[260px] shrink-0">
          <div className="flex gap-4 pb-2 border-b border-line">
            <div className="flex-1">
              <span className="text-[10px] font-mono uppercase tracking-label text-ink">Gated</span>
            </div>
            <div className="flex-1 text-right">
              <span className="text-[10px] font-mono uppercase tracking-label text-muted">B&H</span>
            </div>
          </div>

          <StatCompare label="Total Return" gated={gated.totalReturn - 1} baseline={bench.totalReturn - 1} />
          <StatCompare label="Ann. Return" gated={gated.annualizedReturn} baseline={bench.annualizedReturn} />
          <StatCompare label="Sharpe Ratio" gated={gated.sharpe} baseline={bench.sharpe} format="ratio" />
          <StatCompare label="Max Drawdown" gated={gated.maxDrawdown} baseline={bench.maxDrawdown} higherBetter={false} />
          <StatCompare label="Calmar Ratio" gated={gated.calmar} baseline={bench.calmar} format="ratio" />
        </div>
      </div>
    </div>
  )
}
