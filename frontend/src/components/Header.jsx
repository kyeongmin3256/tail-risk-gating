import React from 'react'

export default function Header() {
  return (
    <header className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        {/* Logo mark */}
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-green flex items-center justify-center">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M2 14L6 6L10 10L14 4L18 8" stroke="#0a0b0f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M14 4L18 4L18 8" stroke="#0a0b0f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <h1 className="font-display text-xl font-bold tracking-tight text-white">
            TailCast
          </h1>
          <p className="text-xs text-white/30 font-mono mt-0.5">
            Conditional Tail Risk Estimation
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-green/10 border border-accent-green/20">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse-dot" />
          <span className="text-xs font-mono text-accent-green">LIVE</span>
        </div>
        <div className="text-right">
          <p className="text-xs text-white/40 font-mono">
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
          </p>
        </div>
      </div>
    </header>
  )
}
