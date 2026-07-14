const INK = '#1F4B6E'
const LINE = '#D9D4C8'
const MUTED = '#5C5A55'

const signalConfig = {
  SAFE:    { color: '#2F6B4F', label: 'Low Risk', text: 'text-up' },
  CAUTION: { color: '#8A6A1F', label: 'Elevated', text: 'text-warn' },
  DANGER:  { color: '#9B3A3A', label: 'High Risk', text: 'text-down' },
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
      <path d={fullArc} fill="none" stroke={LINE} strokeWidth="10" strokeLinecap="round" />
      <path
        d={valueArc}
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        style={{ transition: 'stroke 0.25s ease, d 0.25s ease' }}
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
              fill={active ? INK : '#C8C2B6'}
            />
            <text
              x={pt.x}
              y={pt.y + 14}
              textAnchor="middle"
              fill={active ? INK : MUTED}
              fontSize="8"
              fontFamily="IBM Plex Mono"
            >
              −{t}%
            </text>
          </g>
        )
      })}
      <circle cx={lossPoint.x} cy={lossPoint.y} r="5" fill={INK} stroke="#F3F1EC" strokeWidth="2"
        style={{ transition: 'all 0.2s ease' }} />
      <circle cx={gatePoint.x} cy={gatePoint.y} r="3.5" fill="none" stroke={MUTED} strokeWidth="1.5" />
      <text x={cx} y={cy - 8} textAnchor="middle" fill={INK} fontSize="28" fontWeight="600"
        style={{ transition: 'all 0.2s ease', fontFamily: 'Source Serif 4, Georgia, serif' }}>
        {(probability * 100).toFixed(1)}%
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill={MUTED} fontSize="9" letterSpacing="1.2"
        fontFamily="IBM Plex Mono">
        TAIL RISK PROB
      </text>
      <text x={cx} y={145} textAnchor="middle" fill={MUTED} fontSize="9" fontFamily="IBM Plex Mono">
        GATE @ {(gateThreshold * 100).toFixed(0)}%
      </text>
    </svg>
  )
}

function DriverRow({ driver, index }) {
  const directionColor = {
    risk_increasing: 'text-down',
    risk_decreasing: 'text-up',
    neutral: 'text-muted',
  }
  const directionIcon = {
    risk_increasing: '▲',
    risk_decreasing: '▼',
    neutral: '—',
  }
  const dir = driver.direction in directionColor ? driver.direction : 'neutral'

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-line/80 last:border-0">
      <span className="text-[10px] font-mono text-muted w-4">{index + 1}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-ink-deep truncate">{driver.label || driver.feature}</p>
        <p className="text-[11px] font-mono text-muted mt-0.5">{driver.feature}</p>
      </div>
      <div className="text-right flex items-center gap-2">
        <span className="text-sm font-mono font-medium text-ink-deep">
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
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <div className="lg:col-span-5 flex flex-col items-center">
        <div className="inline-flex items-center gap-2 mb-4">
          <span className="w-2 h-2" style={{ backgroundColor: config.color }} />
          <span className={`text-[10px] font-mono uppercase tracking-label ${config.text}`}>
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
            <span className="text-[10px] font-mono uppercase tracking-label text-muted">
              Loss Tolerance
            </span>
            <span className="font-display text-sm font-semibold text-ink">
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
              <span key={t} className="text-[9px] font-mono text-muted">−{t}%</span>
            ))}
          </div>
          {blendHint && (
            <p className="font-mono text-[10px] text-muted text-center mt-2">
              {blendHint}
            </p>
          )}
        </div>

        <div className="w-full max-w-[300px] mt-5 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-[10px] font-mono uppercase tracking-label text-muted">Gate</p>
            <p className="font-mono text-xs text-ink-deep mt-1">{policy.label}</p>
          </div>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-label text-muted">Data</p>
            <p className="font-mono text-xs text-ink-deep mt-1">{data.date}</p>
          </div>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-label text-muted">WF Folds</p>
            <p className="font-mono text-xs text-ink-deep mt-1">{data.modelInfo.nFolds}</p>
          </div>
        </div>

        <p className="font-mono text-[11px] text-muted text-center mt-4 max-w-[300px] leading-relaxed">
          {signal === 'SAFE' && 'Probability is below the gate — trade as normal.'}
          {signal === 'CAUTION' && 'Approaching the gate — consider reducing exposure.'}
          {signal === 'DANGER' && 'Above the gate — model would skip or scale down.'}
        </p>
      </div>

      <div className="lg:col-span-7 min-w-0">
        <div className="flex items-baseline justify-between mb-4">
          <h3 className="font-display text-base font-semibold text-ink">Top Risk Drivers</h3>
          <span className="text-[10px] font-mono uppercase tracking-label text-muted">SHAP</span>
        </div>
        <div>
          {data.topDrivers.map((driver, i) => (
            <DriverRow key={driver.feature} driver={driver} index={i} />
          ))}
        </div>
      </div>
    </div>
  )
}
