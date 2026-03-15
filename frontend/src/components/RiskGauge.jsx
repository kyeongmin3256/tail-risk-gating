import React from 'react'
import { todayRisk } from '../data/mockData'

const signalConfig = {
  SAFE:    { color: '#00e5a0', label: 'LOW RISK',  glow: 'glow-green',  bg: 'bg-accent-green/8' },
  CAUTION: { color: '#ffb020', label: 'ELEVATED',  glow: 'glow-amber',  bg: 'bg-accent-amber/8' },
  DANGER:  { color: '#ff3b5c', label: 'HIGH RISK', glow: 'glow-red',    bg: 'bg-accent-red/8' },
}

function GaugeSVG({ probability, threshold, color }) {
  const pct = Math.min(probability, 1)
  const threshPct = Math.min(threshold, 1)
  // Arc from -135deg to +135deg (270deg sweep)
  const startAngle = -135
  const sweepAngle = 270
  const r = 80
  const cx = 100
  const cy = 100

  function polarToCartesian(angle) {
    const rad = (angle * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  function describeArc(startA, endA) {
    const start = polarToCartesian(endA)
    const end = polarToCartesian(startA)
    const large = endA - startA > 180 ? 1 : 0
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y}`
  }

  const fullArc = describeArc(startAngle, startAngle + sweepAngle)
  const valueAngle = startAngle + sweepAngle * pct
  const valueArc = describeArc(startAngle, valueAngle)
  const threshAngle = startAngle + sweepAngle * threshPct
  const threshPoint = polarToCartesian(threshAngle)

  return (
    <svg viewBox="0 0 200 160" className="w-full max-w-[280px]">
      {/* Background track */}
      <path d={fullArc} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12" strokeLinecap="round" />
      {/* Value arc */}
      <path d={valueArc} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 8px ${color}40)` }} />
      {/* Threshold marker */}
      <circle cx={threshPoint.x} cy={threshPoint.y} r="4" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="2" />
      <line x1={threshPoint.x} y1={threshPoint.y - 8} x2={threshPoint.x} y2={threshPoint.y + 8}
        stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round"
        transform={`rotate(${threshAngle}, ${threshPoint.x}, ${threshPoint.y})`} />
      {/* Center text */}
      <text x={cx} y={cy - 8} textAnchor="middle" className="font-mono" fill="white" fontSize="32" fontWeight="700">
        {(probability * 100).toFixed(1)}%
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" className="font-mono">
        TAIL RISK PROB
      </text>
      {/* Threshold label */}
      <text x={cx} y={145} textAnchor="middle" fill="rgba(255,255,255,0.25)" fontSize="9" className="font-mono">
        GATE @ {(threshold * 100).toFixed(1)}%
      </text>
    </svg>
  )
}

function DriverRow({ driver, index }) {
  const directionColor = {
    risk_increasing: 'text-accent-red',
    risk_decreasing: 'text-accent-green',
    neutral: 'text-white/40',
  }
  const directionIcon = {
    risk_increasing: '▲',
    risk_decreasing: '▼',
    neutral: '—',
  }

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <span className="text-[10px] font-mono text-white/20 w-4">{index + 1}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white/80 truncate">{driver.description}</p>
        <p className="text-xs font-mono text-white/30 mt-0.5">{driver.feature}</p>
      </div>
      <div className="text-right flex items-center gap-2">
        <span className="text-sm font-mono font-semibold text-white/70">
          {typeof driver.value === 'number' ? driver.value.toFixed(2) : driver.value}
        </span>
        <span className={`text-xs ${directionColor[driver.direction]}`}>
          {directionIcon[driver.direction]}
        </span>
      </div>
    </div>
  )
}

export default function RiskGauge() {
  const config = signalConfig[todayRisk.signal]

  return (
    <div className={`card p-6 ${config.glow}`}>
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Left: Gauge */}
        <div className="flex flex-col items-center justify-center lg:w-[340px] shrink-0">
          <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full ${config.bg} border border-white/5 mb-4`}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
            <span className="text-xs font-mono font-semibold tracking-widest" style={{ color: config.color }}>
              {config.label}
            </span>
          </div>
          <GaugeSVG probability={todayRisk.probability} threshold={todayRisk.threshold} color={config.color} />
          <div className="flex gap-6 mt-2">
            <div className="text-center">
              <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider">Last Train</p>
              <p className="text-xs font-mono text-white/50 mt-1">{todayRisk.modelInfo.lastTrained}</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider">Window</p>
              <p className="text-xs font-mono text-white/50 mt-1">{todayRisk.modelInfo.windowSize}</p>
            </div>
          </div>
        </div>

        {/* Right: Risk Drivers */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="font-display text-sm font-semibold text-white/60 uppercase tracking-wider">
              Today's Risk Drivers
            </h2>
            <span className="text-[10px] font-mono text-white/20 bg-white/5 px-2 py-0.5 rounded">
              SHAP
            </span>
          </div>
          <div>
            {todayRisk.topDrivers.map((driver, i) => (
              <DriverRow key={driver.feature} driver={driver} index={i} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
