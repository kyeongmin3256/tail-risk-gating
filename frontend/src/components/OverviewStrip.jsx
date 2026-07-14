function Metric({ label, value }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
      <span className="text-[10px] font-mono uppercase tracking-label text-muted">{label}</span>
      <span className="font-display text-sm font-semibold text-ink">{value}</span>
    </span>
  )
}

function Divider() {
  return <span className="hidden h-3 w-px bg-line sm:inline-block" aria-hidden />
}

function signalLabel(probability, gateThreshold) {
  if (probability >= gateThreshold) return 'High Risk'
  if (probability >= gateThreshold * 0.7) return 'Elevated'
  return 'Low Risk'
}

export default function OverviewStrip({ asOf, probability, gateThreshold, policyLabel }) {
  return (
    <section className="mt-4 border-b border-line pb-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="font-display text-base font-semibold tracking-tight text-ink">
          System Overview
        </h2>
        <Divider />
        <span className="text-[10px] font-mono uppercase tracking-label text-muted">
          As of {asOf}
        </span>
        <Divider />
        <Metric label="Tail Risk" value={`${(probability * 100).toFixed(1)}%`} />
        <Divider />
        <Metric label="Signal" value={signalLabel(probability, gateThreshold)} />
        <Divider />
        <Metric label="Gate" value={policyLabel} />
      </div>
    </section>
  )
}
