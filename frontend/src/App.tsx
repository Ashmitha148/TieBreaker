import React from 'react'

export const App: React.FC = () => {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl space-y-6">
        <header className="space-y-2 border-b border-slate-800 pb-4">
          <div className="inline-block px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 rounded-full">
            Phase 0 Foundation
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            TieBreaker
          </h1>
          <p className="text-sm text-slate-400">
            Payment Routing &amp; Strike Decision Engine
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            System Status
          </h2>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
              <span className="text-slate-300">Frontend Core</span>
              <span className="inline-flex items-center text-emerald-400 text-xs font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse"></span>
                Active (Vite + React)
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
              <span className="text-slate-300">Backend API</span>
              <span className="inline-flex items-center text-emerald-400 text-xs font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-400 mr-2"></span>
                FastAPI /health (200)
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
              <span className="text-slate-300">Database Layer</span>
              <span className="inline-flex items-center text-blue-400 text-xs font-medium">
                PostgreSQL-Ready
              </span>
            </div>
          </div>
        </section>

        <footer className="pt-2 text-center text-xs text-slate-500">
          Clean architectural foundation &bull; Phase 0
        </footer>
      </div>
    </main>
  )
}

export default App
