import React, { useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { modelMetrics } from '../data/mockData'

function MetricCard({ label, value, sublabel, accent = false }) {
  return (
    <div className="bg-white/[0.02] rounded-lg p-3 border border-white/[0.04]">
      <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-mono font-bold mt-1 ${accent ? 'text-accent-cyan' : 'text-white/90'}`}>
        {value}
      </p>
      {sublabel && <p className="text-[10px] font-mono text-white/20 mt-0.5">{sublabel}</p>}
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-700 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      {payload.map((entry, i) => (
        <p key={i} className="text-xs font-mono" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(3) : entry.value}
        </p>
      ))}
    </div>
  )
}

export default function ModelMetrics() {
  const [tab, setTab] = useState('roc')

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

      {/* Key Metrics Row */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <MetricCard label="ROC-AUC" value={modelMetrics.rocAuc.toFixed(2)} sublabel="Walk-forward avg" accent />
        <MetricCard label="Avg Precision" value={modelMetrics.avgPrecision.toFixed(2)} sublabel="PR-AUC" />
        <MetricCard label="Brier Score" value={modelMetrics.brierScore.toFixed(3)} sublabel="Lower = better" />
      </div>

      {/* Chart */}
      <div className="h-[240px]">
        {tab === 'roc' ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={modelMetrics.rocCurve}>
              <defs>
                <linearGradient id="rocFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06d6d0" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#06d6d0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="fpr"
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5, style: { fill: 'rgba(255,255,255,0.25)', fontSize: 10 } }}
              />
              <YAxis
                dataKey="tpr"
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft', offset: 10, style: { fill: 'rgba(255,255,255,0.25)', fontSize: 10 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                stroke="rgba(255,255,255,0.1)"
                strokeDasharray="4 4"
              />
              <Area
                type="monotone"
                dataKey="tpr"
                stroke="#06d6d0"
                strokeWidth={2}
                fill="url(#rocFill)"
                name="TPR"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={modelMetrics.walkForwardFolds}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis domain={[0.5, 1.0]} tickFormatter={(v) => v.toFixed(1)} />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={modelMetrics.rocAuc} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" label="" />
              <Line
                type="monotone"
                dataKey="auc"
                stroke="#06d6d0"
                strokeWidth={2}
                dot={{ r: 5, fill: '#06d6d0', stroke: '#0a0b0f', strokeWidth: 2 }}
                activeDot={{ r: 7 }}
                name="AUC"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Walk-forward fold table (always visible as detail) */}
      {tab === 'folds' && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-white/25 uppercase tracking-wider">
                <th className="text-left py-2 pr-4">Fold</th>
                <th className="text-left py-2 pr-4">Period</th>
                <th className="text-right py-2 pr-4">AUC</th>
                <th className="text-right py-2 pr-4">Samples</th>
                <th className="text-right py-2">Pos %</th>
              </tr>
            </thead>
            <tbody>
              {modelMetrics.walkForwardFolds.map((fold) => (
                <tr key={fold.fold} className="border-t border-white/[0.04] text-white/60">
                  <td className="py-2 pr-4">{fold.fold}</td>
                  <td className="py-2 pr-4">{fold.period}</td>
                  <td className="py-2 pr-4 text-right text-accent-cyan font-semibold">{fold.auc.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right">{fold.samples}</td>
                  <td className="py-2 text-right">{((fold.positives / fold.samples) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
