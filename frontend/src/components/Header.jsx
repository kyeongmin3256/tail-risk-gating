export default function Header({ status = 'Operational', statusKind = 'ok' }) {
  const statusColor =
    statusKind === 'ok' ? 'bg-up' : statusKind === 'warn' ? 'bg-warn' : 'bg-muted'

  return (
    <header className="flex items-center justify-between border-b border-line pb-5">
      <div className="flex items-baseline gap-2.5">
        <h1 className="font-display text-[1.65rem] font-semibold tracking-tight text-ink">
          TailCast
        </h1>
        <span className="hidden sm:inline text-sm text-muted">
          Conditional Tail Risk Estimation
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-label text-muted">
        <span className={`inline-block h-2 w-2 ${statusColor}`} />
        <span>Status: {status}</span>
      </div>
    </header>
  )
}
