import { useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const INK = '#1F4B6E'
const LINE = '#D9D4C8'
const MUTED = '#5C5A55'
const TICK = { fontSize: 9, fill: MUTED, fontFamily: 'IBM Plex Mono' }
const TOOLTIP_STYLE = {
  background: '#F3F1EC',
  border: '1px solid #D9D4C8',
  fontFamily: 'IBM Plex Mono',
  fontSize: 11,
}

const BENCHMARK_HINTS = {
  'ROC-AUC': 'Random classifier baseline: 0.50',
  'Avg Precision': 'Positive-class base rate (random baseline)',
  'Brier Score': 'Naive constant-probability baseline',
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

function MetricCard({ label, value, sublabel, benchmark, accent = false }) {
  const [hovered, setHovered] = useState(false)
  const benchDelta = benchmark != null ? value - benchmark : null
  const improved = benchDelta != null && (
    label === 'Brier Score' ? benchDelta < 0 : benchDelta > 0
  )

  return (
    <div
      className="relative border-b border-line/80 pb-3 cursor-default"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <p className="text-[10px] font-mono uppercase tracking-label text-muted">{label}</p>
      <p className={`font-display text-2xl font-semibold mt-1 ${accent ? 'text-ink' : 'text-ink-deep'}`}>
        {value}
      </p>
      {sublabel && <p className="text-[10px] font-mono text-muted mt-0.5">{sublabel}</p>}
      {benchmark != null && (
        <p className="text-[10px] font-mono text-muted mt-1">
          vs {benchmark.toFixed(label === 'Brier Score' ? 3 : 2)} baseline
          {benchDelta != null && (
            <span className={improved ? ' text-ink ml-1' : ' text-muted ml-1'}>
              ({benchDelta > 0 ? '+' : ''}{benchDelta.toFixed(label === 'Brier Score' ? 3 : 2)})
            </span>
          )}
        </p>
      )}

      {hovered && (
        <div className="absolute z-20 left-0 right-0 top-full mt-2 border border-line bg-paper px-3 py-2 pointer-events-none">
          <p className="text-[10px] font-mono text-muted leading-relaxed">
            {BENCHMARK_HINTS[label] || 'Walk-forward out-of-sample metric'}
          </p>
        </div>
      )}
    </div>
  )
}

export default function ModelMetrics({ data }) {
  const [tab, setTab] = useState('roc')
  const benchmarks = data.benchmarks || {}

  const foldChartData = data.walkForwardFolds
    .filter(f => f.auc !== null)
    .map(f => ({ ...f }))

  const calibrationChartData = (data.calibration?.predicted || []).map((predicted, i) => ({
    predicted,
    observed: data.calibration.observed[i],
  }))

  const avgAuc = foldChartData.length > 0
    ? foldChartData.reduce((s, f) => s + f.auc, 0) / foldChartData.length
    : data.rocAuc

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5 gap-4">
        <h3 className="font-display text-base font-semibold text-ink">Model Performance</h3>
        <div className="flex gap-2">
          <TabButton active={tab === 'roc'} onClick={() => setTab('roc')}>ROC</TabButton>
          <TabButton active={tab === 'calibration'} onClick={() => setTab('calibration')}>Calibration</TabButton>
          <TabButton active={tab === 'folds'} onClick={() => setTab('folds')}>Walk-Fwd</TabButton>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-5 mb-5">
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

      <div className="h-[260px] border border-line bg-[#EDEAE3]/30 px-1 py-2 sm:px-2">
        {tab === 'roc' ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.rocCurve} margin={{ top: 8, right: 16, bottom: 24, left: 40 }}>
              <CartesianGrid stroke={LINE} strokeDasharray="3 6" vertical={false} />
              <XAxis
                dataKey="fpr"
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={TICK}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                dataKey="tpr"
                type="number"
                domain={[0, 1]}
                width={42}
                tickFormatter={(v) => v.toFixed(1)}
                tick={TICK}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                stroke="#8B8680"
                strokeDasharray="4 4"
              />
              <Area
                type="monotone"
                dataKey="tpr"
                stroke={INK}
                strokeWidth={1.75}
                fill="rgba(31, 75, 110, 0.08)"
                name="TPR"
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : tab === 'calibration' ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={calibrationChartData} margin={{ top: 8, right: 16, bottom: 24, left: 40 }}>
              <CartesianGrid stroke={LINE} strokeDasharray="3 6" vertical={false} />
              <XAxis
                dataKey="predicted"
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={TICK}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                dataKey="observed"
                type="number"
                domain={[0, 1]}
                width={42}
                tickFormatter={(v) => v.toFixed(1)}
                tick={TICK}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                stroke="#8B8680"
                strokeDasharray="4 4"
              />
              <Line
                type="monotone"
                dataKey="observed"
                stroke={INK}
                strokeWidth={1.75}
                dot={{ r: 3, fill: INK, stroke: '#F3F1EC', strokeWidth: 2 }}
                name="Observed"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={foldChartData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid stroke={LINE} strokeDasharray="3 6" vertical={false} />
              <XAxis
                dataKey="period"
                tick={TICK}
                interval={Math.floor(foldChartData.length / 6)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0.4, 1.0]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={TICK}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <ReferenceLine y={avgAuc} stroke="#8B8680" strokeDasharray="4 4" />
              <Line
                type="monotone"
                dataKey="auc"
                stroke={INK}
                strokeWidth={1.75}
                dot={{ r: 2.5, fill: INK, stroke: '#F3F1EC', strokeWidth: 1.5 }}
                name="AUC"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {tab === 'folds' && (
        <div className="mt-4 overflow-x-auto max-h-[200px] overflow-y-auto">
          <table className="w-full text-xs font-mono">
            <thead className="sticky top-0 bg-paper">
              <tr className="text-muted uppercase tracking-label">
                <th className="text-left py-2 pr-4 font-medium">Fold</th>
                <th className="text-left py-2 pr-4 font-medium">Period</th>
                <th className="text-right py-2 pr-4 font-medium">AUC</th>
                <th className="text-right py-2 pr-4 font-medium">Samples</th>
                <th className="text-right py-2 font-medium">Pos %</th>
              </tr>
            </thead>
            <tbody>
              {data.walkForwardFolds.map((fold) => (
                <tr key={fold.fold} className="border-t border-line/80 text-muted">
                  <td className="py-2 pr-4">{fold.fold}</td>
                  <td className="py-2 pr-4">{fold.period}</td>
                  <td className="py-2 pr-4 text-right text-ink font-semibold">
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
