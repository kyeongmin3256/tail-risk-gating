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

function GaugeSVG({ probability, gateThreshold, lossTolerance, thresholds, color }) {
  const pct = Math.min(probability, 1)
  const startAngle = -135
  const sweepAngle = 270
  const r = 80
  const cx = 100
  const cy = 100
  const minT = Math.min(...thresholds)
  const maxT = Math.max(...thresholds)

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
  const gateAngle = startAngle + sweepAngle * Math.min(gateThreshold, 1)
  const gatePoint = polarToCartesian(gateAngle)
  const lossNorm = (lossTolerance - minT) / (maxT - minT)
  const lossAngle = startAngle + sweepAngle * lossNorm
  const lossPoint = polarToCartesian(lossAngle)

  return (
    <svg viewBox="0 0 200 160" className="w-full max-w-[280px]">
      <path d={fullArc} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12" strokeLinecap="round" />
      <path
        d={valueArc}
        fill="none"
        stroke={color}
        strokeWidth="12"
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 8px ${color}40)`, transition: 'stroke 0.25s ease, d 0.25s ease' }}
      />
      {thresholds.map((t) => {
        const norm = (t - minT) / (maxT - minT)
        const angle = startAngle + sweepAngle * norm
        const pt = polarToCartesian(angle)
        const active = Math.abs(t - lossTolerance) < 0.25
        return (
          <g key={t}>
            <circle
              cx={pt.x}
              cy={pt.y}
              r={active ? 3.5 : 2}
              fill={active ? '#06d6d0' : 'rgba(255,255,255,0.15)'}
            />
            <text
              x={pt.x}
              y={pt.y + 14}
              textAnchor="middle"
              fill={active ? 'rgba(6,214,208,0.9)' : 'rgba(255,255,255,0.2)'}
              fontSize="8"
              className="font-mono"
            >
              −{t}%
            </text>
          </g>
        )
      })}
      <circle cx={lossPoint.x} cy={lossPoint.y} r="5" fill="#06d6d0" stroke="#0a0b0f" strokeWidth="2"
        style={{ transition: 'all 0.2s ease' }} />
      <circle cx={gatePoint.x} cy={gatePoint.y} r="3.5" fill="none" stroke="rgba(255,255,255,0.45)" strokeWidth="2" />
      <text x={cx} y={cy - 8} textAnchor="middle" className="font-mono" fill="white" fontSize="32" fontWeight="700"
        style={{ transition: 'all 0.2s ease' }}>
        {(probability * 100).toFixed(1)}%
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" className="font-mono">
        TAIL RISK PROB
      </text>
      <text x={cx} y={145} textAnchor="middle" fill="rgba(255,255,255,0.25)" fontSize="9" className="font-mono">
        GATE @ {(gateThreshold * 100).toFixed(0)}%
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
  const dir = driver.direction in directionColor ? driver.direction : 'neutral'

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <span className="text-[10px] font-mono text-white/20 w-4">{index + 1}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white/80 truncate">{driver.label || driver.feature}</p>
        <p className="text-xs font-mono text-white/30 mt-0.5">{driver.feature}</p>
      </div>
      <div className="text-right flex items-center gap-2">
        <span className="text-sm font-mono font-semibold text-white/70">
          {typeof driver.shapValue === 'number' ? driver.shapValue.toFixed(4) : driver.shapValue}
        </span>
        <span className={`text-xs ${directionColor[dir]}`}>
          {directionIcon[dir]}
        </span>
      </div>
    </div>
  )
}

export default function RiskGauge({
  data,
  gatingPolicy,
  lossTolerance,
  onLossToleranceChange,
  thresholds,
  blendHint,
}) {
  const policy = gatingPolicy ?? {
    gateThreshold: 0.15,
    mode: 'hard',
    label: 'Hard Gate @ 15%',
  }
  const gateThreshold = policy.gateThreshold
  const signal = getSignal(data.probability, gateThreshold)
  const config = signalConfig[signal]
  const minT = Math.min(...thresholds)
  const maxT = Math.max(...thresholds)

  return (
    <div className={`card p-6 ${config.glow}`} style={{ transition: 'box-shadow 0.3s ease' }}>
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex flex-col items-center justify-center lg:w-[360px] shrink-0">
          <div
            className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full ${config.bg} border border-white/5 mb-4`}
            style={{ transition: 'all 0.3s ease' }}
          >
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
            <span className="text-xs font-mono font-semibold tracking-widest" style={{ color: config.color }}>
              {config.label}
            </span>
          </div>

          <GaugeSVG
            probability={data.probability}
            gateThreshold={gateThreshold}
            lossTolerance={lossTolerance}
            thresholds={thresholds}
            color={config.color}
          />

          <div className="w-full max-w-[300px] mt-5 px-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
                Loss Tolerance
              </span>
              <span className="text-sm font-mono font-semibold text-accent-cyan">
                −{lossTolerance.toFixed(1)}%
              </span>
            </div>
            <input
              type="range"
              min={minT * 10}
              max={maxT * 10}
              step={1}
              value={Math.round(lossTolerance * 10)}
              onChange={(e) => onLossToleranceChange(Number(e.target.value) / 10)}
              className="loss-tolerance-slider w-full"
            />
            <div className="flex justify-between mt-1.5">
              {thresholds.map((t) => (
                <span key={t} className="text-[9px] font-mono text-white/20">−{t}%</span>
              ))}
            </div>
            {blendHint && (
              <p className="text-[10px] font-mono text-accent-cyan/60 text-center mt-2">
                {blendHint}
              </p>
            )}
          </div>

          <div className="w-full max-w-[300px] mt-4 px-1 text-center">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
              Gating Policy
            </p>
            <p className="text-xs font-mono text-white/55 mt-1">{policy.label}</p>
            <p className="text-[10px] text-white/22 mt-2 leading-relaxed">
              {signal === 'SAFE' && 'Probability is below the gate — trade as normal.'}
              {signal === 'CAUTION' && 'Approaching the gate — consider reducing exposure.'}
              {signal === 'DANGER' && 'Above the gate — model would skip or scale down.'}
            </p>
          </div>

          <div className="flex gap-6 mt-4">
            <div className="text-center">
              <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider">Data Through</p>
              <p className="text-xs font-mono text-white/50 mt-1">{data.date}</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider">WF Folds</p>
              <p className="text-xs font-mono text-white/50 mt-1">{data.modelInfo.nFolds}</p>
            </div>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="font-display text-sm font-semibold text-white/60 uppercase tracking-wider">
              Top Risk Drivers
            </h2>
            <span className="text-[10px] font-mono text-white/20 bg-white/5 px-2 py-0.5 rounded">
              SHAP
            </span>
          </div>
          <div>
            {data.topDrivers.map((driver, i) => (
              <DriverRow key={driver.feature} driver={driver} index={i} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
