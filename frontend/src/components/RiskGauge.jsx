const INK = '#1F4B6E'
const LINE = '#D9D4C8'
const MUTED = '#5C5A55'
const UP = '#2F6B4F'
const DOWN = '#9B3A3A'

const signalConfig = {
  SAFE:    { color: UP, label: 'Low Risk', text: 'text-up' },
  CAUTION: { color: '#8A6A1F', label: 'Elevated', text: 'text-warn' },
  DANGER:  { color: DOWN, label: 'High Risk', text: 'text-down' },
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
  const r = 72
  const cx = 100
  const cy = 98
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
    <svg
      viewBox="0 0 200 188"
      className="mx-auto w-full max-w-[200px]"
      role="img"
      aria-label={`Tail risk probability ${(probability * 100).toFixed(1)} percent`}
    >
      <path d={fullArc} fill="none" stroke={LINE} strokeWidth="9" strokeLinecap="round" />
      <path
        d={valueArc}
        fill="none"
        stroke={color}
        strokeWidth="9"
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
              y={pt.y + (pt.y > cy ? 12 : -8)}
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
      <circle cx={lossPoint.x} cy={lossPoint.y} r="4.5" fill={INK} stroke="#F3F1EC" strokeWidth="2" />
      <circle cx={gatePoint.x} cy={gatePoint.y} r="3" fill="none" stroke={MUTED} strokeWidth="1.5" />
      <text
        x={cx}
        y={cy - 6}
        textAnchor="middle"
        fill={INK}
        fontSize="26"
        fontWeight="600"
        style={{ fontFamily: 'Source Serif 4, Georgia, serif', transition: 'opacity 0.2s ease' }}
      >
        {(probability * 100).toFixed(1)}%
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" fill={MUTED} fontSize="8" letterSpacing="1.2" fontFamily="IBM Plex Mono">
        TAIL RISK PROB
      </text>
      <text x={cx} y={176} textAnchor="middle" fill={MUTED} fontSize="8" fontFamily="IBM Plex Mono">
        GATE @ {(gateThreshold * 100).toFixed(0)}%
      </text>
    </svg>
  )
}

function LossToleranceControl({ lossTolerance, thresholds, onChange, blendHint }) {
  const minT = Math.min(...thresholds)
  const maxT = Math.max(...thresholds)
  const onExactThreshold = thresholds.some((t) => Math.abs(t - lossTolerance) < 0.05)
  const fillPct = ((lossTolerance - minT) / (maxT - minT)) * 100

  return (
    <div className="border border-ink/15 bg-[#EDEAE3]/50 p-3 sm:p-4">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <span className="text-[10px] font-mono uppercase tracking-label text-muted">
          Loss Tolerance
        </span>
        <span
          key={lossTolerance}
          className="font-display text-2xl font-semibold text-ink tabular-nums animate-tol-pop"
        >
          −{lossTolerance.toFixed(1)}%
        </span>
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        {thresholds.map((t) => {
          const active = Math.abs(t - lossTolerance) < 0.05
          return (
            <button
              key={t}
              type="button"
              onClick={() => onChange(t)}
              className={`loss-tol-pill ${active ? 'loss-tol-pill-active' : ''}`}
              aria-pressed={active}
            >
              −{t}%
            </button>
          )
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-line/80">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[9px] font-mono uppercase tracking-label text-muted">
            Fine tune
          </span>
          <span className="text-[9px] font-mono text-muted">
            −{minT}% … −{maxT}%
          </span>
        </div>
        <input
          type="range"
          min={minT * 10}
          max={maxT * 10}
          step={1}
          value={Math.round(lossTolerance * 10)}
          onChange={(e) => onChange(Number(e.target.value) / 10)}
          className="loss-tolerance-slider w-full"
          style={{ '--fill': `${fillPct}%` }}
          aria-label="Fine-tune loss tolerance between model thresholds"
        />
      </div>

      {blendHint && (
        <p className="font-mono text-[10px] text-ink/80 mt-2.5 px-2 py-1.5 bg-ink/5 border border-ink/10">
          {blendHint}
        </p>
      )}

      {!onExactThreshold && !blendHint && (
        <p className="font-mono text-[10px] text-muted mt-2">
          Interpolating between adjacent models
        </p>
      )}
    </div>
  )
}

function DriverRow({ driver, index, maxAbs }) {
  const directionColor = {
    risk_increasing: DOWN,
    risk_decreasing: UP,
    neutral: MUTED,
  }
  const directionIcon = {
    risk_increasing: '▲',
    risk_decreasing: '▼',
    neutral: '—',
  }
  const dir = driver.direction in directionColor ? driver.direction : 'neutral'
  const magnitude = Math.abs(typeof driver.shapValue === 'number' ? driver.shapValue : 0)
  const barWidth = maxAbs > 0 ? (magnitude / maxAbs) * 100 : 0

  return (
    <div className="grid grid-cols-[1rem_minmax(0,9rem)_1fr_3.5rem_1rem] items-center gap-x-2 py-1.5 border-b border-line/70 last:border-0">
      <span className="text-[10px] font-mono text-muted">{index + 1}</span>
      <div className="min-w-0 truncate">
        <span className="text-xs text-ink-deep">{driver.label || driver.feature}</span>
      </div>
      <div className="h-2 bg-line/60 relative overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 transition-all duration-300 ease-out"
          style={{
            width: `${barWidth}%`,
            backgroundColor: directionColor[dir],
            opacity: 0.85,
          }}
        />
      </div>
      <span className="font-mono text-[11px] text-ink-deep tabular-nums text-right">
        {typeof driver.shapValue === 'number' ? driver.shapValue.toFixed(4) : driver.shapValue}
      </span>
      <span
        className="text-[10px] text-right"
        style={{ color: directionColor[dir] }}
      >
        {directionIcon[dir]}
      </span>
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
  const maxAbs = Math.max(
    ...data.topDrivers.map((d) => Math.abs(typeof d.shapValue === 'number' ? d.shapValue : 0)),
    0.0001,
  )

  const signalHint =
    signal === 'SAFE'
      ? 'Below gate — trade as normal.'
      : signal === 'CAUTION'
        ? 'Approaching gate — consider reducing exposure.'
        : 'Above gate — skip or scale down.'

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,200px)_1fr] gap-4 md:gap-6 items-start">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2" style={{ backgroundColor: config.color }} />
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

          <p className="font-mono text-[10px] text-muted leading-relaxed text-center md:text-left">
            {signalHint}
          </p>
        </div>

        <LossToleranceControl
          lossTolerance={lossTolerance}
          thresholds={thresholds}
          onChange={onLossToleranceChange}
          blendHint={blendHint}
        />
      </div>

      <div className="border-t border-line pt-3">
        <div className="flex items-baseline justify-between mb-2">
          <h3 className="font-display text-sm font-semibold text-ink">Top Risk Drivers</h3>
          <span className="text-[10px] font-mono uppercase tracking-label text-muted">
            SHAP · WF {data.modelInfo.nFolds}
          </span>
        </div>
        <div className="grid grid-cols-[1rem_minmax(0,9rem)_1fr_3.5rem_1rem] gap-x-2 px-0 mb-1">
          <span />
          <span className="text-[9px] font-mono uppercase tracking-label text-muted">Feature</span>
          <span className="text-[9px] font-mono uppercase tracking-label text-muted">Impact</span>
          <span className="text-[9px] font-mono uppercase tracking-label text-muted text-right">SHAP</span>
          <span />
        </div>
        {data.topDrivers.map((driver, i) => (
          <DriverRow key={driver.feature} driver={driver} index={i} maxAbs={maxAbs} />
        ))}
      </div>
    </div>
  )
}
