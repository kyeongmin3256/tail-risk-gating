import React, { useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'

const BENCHMARK_HINTS = {
  'ROC-AUC': 'Random classifier baseline: 0.50',
  'Avg Precision': 'Positive-class base rate (random baseline)',
  'Brier Score': 'Naive constant-probability baseline',
}

function MetricCard({ label, value, sublabel, benchmark, accent = false }) {
  const [hovered, setHovered] = useState(false)
  const benchDelta = benchmark != null ? value - benchmark : null
  const improved = benchDelta != null && (
    label === 'Brier Score' ? benchDelta < 0 : benchDelta > 0
  )

  return (
    <div
      className="relative bg-white/[0.02] rounded-lg p-3 border border-white/[0.04] transition-colors hover:border-white/[0.12] hover:bg-white/[0.04] cursor-default"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-mono font-bold mt-1 ${accent ? 'text-accent-cyan' : 'text-white/90'}`}>
        {value}
      </p>
      {sublabel && <p className="text-[10px] font-mono text-white/20 mt-0.5">{sublabel}</p>}
      {benchmark != null && (
        <p className="text-[10px] font-mono text-white/25 mt-1">
          vs {benchmark.toFixed(label === 'Brier Score' ? 3 : 2)} baseline
          {benchDelta != null && (
            <span className={improved ? ' text-accent-cyan ml-1' : ' text-white/35 ml-1'}>
              ({benchDelta > 0 ? '+' : ''}{benchDelta.toFixed(label === 'Brier Score' ? 3 : 2)})
            </span>
          )}
        </p>
      )}

      {hovered && (
        <div className="absolute z-20 left-0 right-0 top-full mt-2 bg-surface-700 border border-white/10 rounded-lg px-3 py-2 shadow-xl pointer-events-none">
          <p className="text-[10px] font-mono text-white/50 leading-relaxed">
            {BENCHMARK_HINTS[label] || 'Walk-forward out-of-sample metric'}
          </p>
          {benchmark != null && (
            <p className="text-[10px] font-mono text-accent-cyan/80 mt-1">
              Model {value} · Baseline {benchmark.toFixed(label === 'Brier Score' ? 3 : 2)}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-700 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      {label != null && (
        <p className="text-[10px] font-mono text-white/40 mb-1">{label}</p>
      )}
      {payload.map((entry, i) => (
        <p key={i} className="text-xs font-mono" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(3) : entry.value}
        </p>
      ))}
    </div>
  )
}

function RocTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const pt = payload[0]?.payload
  if (!pt) return null
  return (
    <div className="bg-surface-700 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs font-mono text-white/70">
        FPR: {pt.fpr?.toFixed(3)} · TPR: {pt.tpr?.toFixed(3)}
      </p>
      <p className="text-[10px] font-mono text-white/35 mt-1">
        Random baseline on diagonal (0.50 AUC)
      </p>
    </div>
  )
}

export default function ModelMetrics({ data }) {
  const [tab, setTab] = useState('roc')
  const benchmarks = data.benchmarks || {}

  const foldChartData = data.walkForwardFolds
    .filter(f => f.auc !== null)
    .map(f => ({ ...f }))

  const avgAuc = foldChartData.length > 0
    ? foldChartData.reduce((s, f) => s + f.auc, 0) / foldChartData.length
    : data.rocAuc

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-display text-sm font-semibold text-white/60 uppercase tracking-wider">
          Model Performance
        </h2>
        <div className="flex bg-white/[0.04] rounded-lg p-0.5">
          {['roc', 'folds'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-[11px] font-mono px-3 py-1 rounded-md transition-all ${
                tab === t
                  ? 'bg-white/10 text-white'
                  : 'text-white/30 hover:text-white/50'
              }`}
            >
              {t === 'roc' ? 'ROC Curve' : 'Walk-Forward'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <MetricCard
          label="ROC-AUC"
          value={data.rocAuc.toFixed(2)}
          sublabel="Walk-forward OOS"
          benchmark={benchmarks.rocAuc ?? 0.5}
          accent
        />
        <MetricCard
          label="Avg Precision"
          value={data.avgPrecision.toFixed(2)}
          sublabel="PR-AUC"
          benchmark={benchmarks.avgPrecision ?? 0.07}
        />
        <MetricCard
          label="Brier Score"
          value={data.brierScore.toFixed(3)}
          sublabel="Lower = better"
          benchmark={benchmarks.brierScore ?? 0.061}
        />
      </div>

      <div className="h-[260px]">
        {tab === 'roc' ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data.rocCurve}
              margin={{ top: 8, right: 16, bottom: 24, left: 56 }}
            >
              <defs>
                <linearGradient id="rocFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06d6d0" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#06d6d0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="fpr"
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }}
                label={{
                  value: 'False Positive Rate',
                  position: 'insideBottom',
                  offset: -8,
                  style: { fill: 'rgba(255,255,255,0.25)', fontSize: 10 },
                }}
              />
              <YAxis
                dataKey="tpr"
                type="number"
                domain={[0, 1]}
                width={48}
                tickFormatter={(v) => v.toFixed(1)}
                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }}
                label={{
                  value: 'True Positive Rate',
                  angle: -90,
                  position: 'insideLeft',
                  offset: 12,
                  style: { fill: 'rgba(255,255,255,0.25)', fontSize: 10 },
                }}
              />
              <Tooltip content={<RocTooltip />} />
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                stroke="rgba(255,255,255,0.15)"
                strokeDasharray="4 4"
                label={{
                  value: 'Random (0.50)',
                  position: 'insideTopLeft',
                  fill: 'rgba(255,255,255,0.25)',
                  fontSize: 9,
                }}
              />
              <Area
                type="monotone"
                dataKey="tpr"
                stroke="#06d6d0"
                strokeWidth={2}
                fill="url(#rocFill)"
                name="TPR"
                activeDot={{ r: 5, stroke: '#06d6d0', strokeWidth: 2, fill: '#0a0b0f' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={foldChartData}
              margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.35)' }}
                interval={Math.floor(foldChartData.length / 6)}
              />
              <YAxis
                domain={[0.4, 1.0]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }}
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine
                y={avgAuc}
                stroke="rgba(255,255,255,0.15)"
                strokeDasharray="4 4"
                label={{
                  value: `Avg ${avgAuc.toFixed(2)}`,
                  position: 'insideTopRight',
                  fill: 'rgba(255,255,255,0.25)',
                  fontSize: 9,
                }}
              />
              <Line
                type="monotone"
                dataKey="auc"
                stroke="#06d6d0"
                strokeWidth={2}
                dot={{ r: 3, fill: '#06d6d0', stroke: '#0a0b0f', strokeWidth: 2 }}
                activeDot={{ r: 6, stroke: '#06d6d0', strokeWidth: 2, fill: '#fff' }}
                name="AUC"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {tab === 'folds' && (
        <div className="mt-4 overflow-x-auto max-h-[200px] overflow-y-auto">
          <table className="w-full text-xs font-mono">
            <thead className="sticky top-0 bg-surface-800">
              <tr className="text-white/25 uppercase tracking-wider">
                <th className="text-left py-2 pr-4">Fold</th>
                <th className="text-left py-2 pr-4">Period</th>
                <th className="text-right py-2 pr-4">AUC</th>
                <th className="text-right py-2 pr-4">Samples</th>
                <th className="text-right py-2">Pos %</th>
              </tr>
            </thead>
            <tbody>
              {data.walkForwardFolds.map((fold) => (
                <tr key={fold.fold} className="border-t border-white/[0.04] text-white/60">
                  <td className="py-2 pr-4">{fold.fold}</td>
                  <td className="py-2 pr-4">{fold.period}</td>
                  <td className="py-2 pr-4 text-right text-accent-cyan font-semibold">
                    {fold.auc !== null ? fold.auc.toFixed(2) : '—'}
                  </td>
                  <td className="py-2 pr-4 text-right">{fold.samples}</td>
                  <td className="py-2 text-right">
                    {fold.samples > 0 ? ((fold.positives / fold.samples) * 100).toFixed(1) : '0.0'}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
