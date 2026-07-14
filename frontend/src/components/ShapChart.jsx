import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const BAR_COLORS = {
  risk_increasing: '#9B3A3A',
  risk_decreasing: '#2F6B4F',
  mixed: '#8A6A1F',
}

const DIRECTION_LABELS = {
  risk_increasing: 'increases tail risk',
  risk_decreasing: 'decreases tail risk',
  mixed: 'mixed effect',
}

const TOOLTIP_STYLE = {
  background: '#F3F1EC',
  border: '1px solid #D9D4C8',
  fontFamily: 'IBM Plex Mono',
  fontSize: 11,
}

function ShapTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const color = BAR_COLORS[d.direction] || BAR_COLORS.mixed
  return (
    <div style={TOOLTIP_STYLE} className="px-3 py-2">
      <p className="text-xs font-semibold text-ink-deep">{d.feature}</p>
      <p className="text-xs mt-1" style={{ color }}>
        |SHAP|: {d.importance.toFixed(4)}
      </p>
      <p className="text-[10px] text-muted mt-0.5">
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
    <div>
      <div className="flex items-baseline justify-between mb-5 gap-4">
        <div>
          <h3 className="font-display text-base font-semibold text-ink">SHAP Feature Importance</h3>
          <p className="text-[10px] font-mono text-muted mt-1">
            Mean |SHAP| across walk-forward folds
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAll(!showAll)}
          className="border border-line px-3 py-1 font-mono text-[11px] uppercase tracking-label text-muted transition hover:border-muted hover:text-ink-deep"
        >
          {showAll ? 'Top 10' : `All ${data.length}`}
        </button>
      </div>

      <div className="flex gap-5 mb-4">
        {[
          { key: 'risk_increasing', label: 'Risk ↑' },
          { key: 'risk_decreasing', label: 'Risk ↓' },
          { key: 'mixed', label: 'Mixed' },
        ].map(({ key, label }) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5" style={{ backgroundColor: BAR_COLORS[key] }} />
            <span className="text-[10px] font-mono text-muted">{label}</span>
          </div>
        ))}
      </div>

      <div className={`border border-line bg-[#EDEAE3]/30 px-1 py-2 sm:px-2 ${showAll ? 'h-[400px]' : 'h-[320px]'}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={display}
            layout="vertical"
            margin={{ top: 0, right: 16, bottom: 0, left: 4 }}
          >
            <CartesianGrid strokeDasharray="3 6" horizontal={false} stroke="#D9D4C8" />
            <XAxis
              type="number"
              domain={[0, maxVal * 1.1]}
              tickFormatter={(v) => v.toFixed(3)}
              tick={{ fontSize: 9, fill: '#5C5A55', fontFamily: 'IBM Plex Mono' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="feature"
              width={130}
              tick={{ fontSize: 10, fill: '#5C5A55', fontFamily: 'IBM Plex Mono' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<ShapTooltip />} cursor={{ fill: 'rgba(31, 75, 110, 0.04)' }} />
            <Bar
              dataKey="importance"
              radius={[0, 0, 0, 0]}
              maxBarSize={16}
              onMouseLeave={() => setHoveredFeature(null)}
            >
              {display.map((entry) => (
                <Cell
                  key={entry.feature}
                  fill={barColor(entry.direction)}
                  fillOpacity={hoveredFeature && hoveredFeature !== entry.feature ? 0.35 : 0.9}
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
