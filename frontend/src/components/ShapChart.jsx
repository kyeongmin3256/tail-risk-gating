import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const BAR_COLORS = {
  risk_increasing: '#ff3b5c',
  risk_decreasing: '#00e5a0',
  mixed: '#ffb020',
}

const DIRECTION_LABELS = {
  risk_increasing: 'increases tail risk',
  risk_decreasing: 'decreases tail risk',
  mixed: 'mixed effect',
}

function ShapTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const color = BAR_COLORS[d.direction] || BAR_COLORS.mixed
  return (
    <div className="bg-surface-700 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs font-semibold text-white/90">{d.feature}</p>
      <p className="text-xs font-mono mt-1" style={{ color }}>
        |SHAP|: {d.importance.toFixed(4)}
      </p>
      <p className="text-[10px] font-mono text-white/40 mt-0.5">
        {DIRECTION_LABELS[d.direction] || d.direction}
      </p>
    </div>
  )
}

function barColor(direction) {
  return BAR_COLORS[direction] ?? BAR_COLORS.mixed
}

export default function ShapChart({ data }) {
  const [showAll, setShowAll] = useState(false)
  const [hoveredFeature, setHoveredFeature] = useState(null)
  const display = showAll ? data : data.slice(0, 10)
  const maxVal = Math.max(...display.map(d => d.importance))

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-display text-sm font-semibold text-white/60 uppercase tracking-wider">
            SHAP Feature Importance
          </h2>
          <p className="text-[10px] font-mono text-white/25 mt-1">
            Mean |SHAP| across walk-forward folds
          </p>
        </div>
        <button
          onClick={() => setShowAll(!showAll)}
          className="text-[11px] font-mono text-white/30 hover:text-white/60 transition-colors px-3 py-1 rounded-md bg-white/[0.04] hover:bg-white/[0.08]"
        >
          {showAll ? 'Top 10' : `All ${data.length}`}
        </button>
      </div>

      <div className="flex gap-4 mb-4">
        {[
          { key: 'risk_increasing', label: 'Risk ↑' },
          { key: 'risk_decreasing', label: 'Risk ↓' },
          { key: 'mixed', label: 'Mixed' },
        ].map(({ key, label }) => (
          <div key={key} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: BAR_COLORS[key] }}
            />
            <span className="text-[10px] font-mono text-white/35">{label}</span>
          </div>
        ))}
      </div>

      <div className={showAll ? 'h-[400px]' : 'h-[320px]'}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={display}
            layout="vertical"
            margin={{ top: 0, right: 16, bottom: 0, left: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.06)" />
            <XAxis
              type="number"
              domain={[0, maxVal * 1.1]}
              tickFormatter={(v) => v.toFixed(3)}
              tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }}
            />
            <YAxis
              type="category"
              dataKey="feature"
              width={130}
              tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
            />
            <Tooltip content={<ShapTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar
              dataKey="importance"
              radius={[0, 4, 4, 0]}
              maxBarSize={20}
              onMouseLeave={() => setHoveredFeature(null)}
            >
              {display.map((entry) => (
                <Cell
                  key={entry.feature}
                  fill={barColor(entry.direction)}
                  fillOpacity={hoveredFeature && hoveredFeature !== entry.feature ? 0.35 : 0.85}
                  onMouseEnter={() => setHoveredFeature(entry.feature)}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
