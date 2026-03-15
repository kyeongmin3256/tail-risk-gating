import React, { useState } from 'react'
import { todayRisk } from '../data/mockData'

const signalConfig = {
  SAFE:    { color: '#00e5a0', label: 'LOW RISK',  glow: 'glow-green',  bg: 'bg-accent-green/8' },
  CAUTION: { color: '#ffb020', label: 'ELEVATED',  glow: 'glow-amber',  bg: 'bg-accent-amber/8' },
  DANGER:  { color: '#ff3b5c', label: 'HIGH RISK', glow: 'glow-red',    bg: 'bg-accent-red/8' },
}

function getSignal(probability, threshold) {
  if (probability >= threshold) return 'DANGER'
  if (probability >= threshold * 0.7) return 'CAUTION'
  return 'SAFE'
}

function GaugeSVG({ probability, threshold, color }) {
  const pct = Math.min(probability, 1)
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
  const threshAngle = startAngle + sweepAngle * Math.min(threshold, 1)
  const threshPoint = polarToCartesian(threshAngle)

  return (
    <svg viewBox="0 0 200 160" className="w-full max-w-[280px]">
      <path d={fullArc} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12" strokeLinecap="round" />
      <path d={valueArc} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 8px ${color}40)`, transition: 'stroke 0.3s ease' }} />
      <circle cx={threshPoint.x} cy={threshPoint.y} r="4" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="2"
        style={{ transition: 'all 0.3s ease' }} />
      <line x1={threshPoint.x} y1={threshPoint.y - 8} x2={threshPoint.x} y2={threshPoint.y + 8}
        stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round"
        transform={`rotate(${threshAngle}, ${threshPoint.x}, ${threshPoint.y})`}
        style={{ transition: 'all 0.3s ease' }} />
      <text x={cx} y={cy - 8} textAnchor="middle" className="font-mono" fill="white" fontSize="32" fontWeight="700">
        {(probability * 100).toFixed(1)}%
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" className="font-mono">
        TAIL RISK PROB
      </text>
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
  const [threshold, setThreshold] = useState(todayRisk.threshold)
  const signal = getSignal(todayRisk.probability, threshold)
  const config = signalConfig[signal]

  return (
    <div className={`card p-6 ${config.glow}`} style={{ transition: 'box-shadow 0.3s ease' }}>
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Left: Gauge + Slider */}
        <div className="flex flex-col items-center justify-center lg:w-[340px] shrink-0">
          <div
            className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full ${config.bg} border border-white/5 mb-4`}
            style={{ transition: 'all 0.3s ease' }}
          >
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color, transition: 'background-color 0.3s ease' }} />
            <span className="text-xs font-mono font-semibold tracking-widest" style={{ color: config.color, transition: 'color 0.3s ease' }}>
              {config.label}
            </span>
          </div>
          <GaugeSVG probability={todayRisk.probability} threshold={threshold} color={config.color} />

          {/* Risk Tolerance Slider */}
          <div className="w-full max-w-[280px] mt-4 px-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-white/25 uppercase tracking-wider">
                Your Risk Tolerance
              </span>
              <span className="text-xs font-mono font-semibold" style={{ color: config.color, transition: 'color 0.3s ease' }}>
                {(threshold * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="5"
              max="50"
              step="1"
              value={Math.round(threshold * 100)}
              onChange={(e) => setThreshold(Number(e.target.value) / 100)}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
              style={{
                background: 'linear-gradient(to right, #00e5a0, #ffb020 50%, #ff3b5c)',
              }}
            />
            <div className="flex justify-between mt-1">
              <span className="text-[9px] font-mono text-accent-green/50">Conservative 5%</span>
              <span className="text-[9px] font-mono text-accent-red/50">Aggressive 50%</span>
            </div>
            <p className="text-[10px] text-white/20 text-center mt-2 leading-relaxed">
              {signal === 'SAFE' && 'Model probability is below your threshold — safe to trade.'}
              {signal === 'CAUTION' && 'Approaching your threshold — consider reducing exposure.'}
              {signal === 'DANGER' && 'Exceeds your threshold — gate recommended.'}
            </p>
          </div>

          <div className="flex gap-6 mt-4">
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
