import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { API_URL, apiHeaders } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { Brain } from 'lucide-react'

export default function Learning() {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/learning/override-stats`, { headers: apiHeaders() })
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(d => { setData(d); setLoading(false) })
      .catch((e) => {
        setError(e?.message || 'Could not load override stats')
        setLoading(false)
      })
  }, [])

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1200px]">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-white">Override Learning</h1>
            <p className="text-[12px] text-[#475569] font-mono">Live override rates from this deployment — no invented before/after scores</p>
          </div>

          {loading && <div className="text-[#94a3b8] text-sm">Loading override stats…</div>}
          {error && <div className="text-rose-400 text-sm">{error}. Set VITE_API_KEY to match TIEBREAKER_API_KEY if this endpoint is protected.</div>}

          {data && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[
                  { key: 'total_decisions', label: 'Decisions' },
                  { key: 'total_overrides', label: 'Overrides' },
                  { key: 'override_rate_percent', label: 'All-time override %' },
                  { key: 'recent_override_rate_percent', label: '7-day override %' },
                ].map((m, i) => (
                  <motion.div key={m.key} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.05 }}
                    className="float-card p-5 text-center">
                    <div className="text-[10px] text-[#475569] uppercase tracking-wider font-bold mb-1">{m.label}</div>
                    <div className="text-2xl font-bold text-white font-data">{data[m.key] ?? '—'}</div>
                  </motion.div>
                ))}
              </div>

              <div className="float-card p-5">
                <div className="px-1 pb-4 flex items-center gap-2">
                  <Brain className="w-4 h-4 text-[#3395FF]" />
                  <span className="label">Retrain recommendation</span>
                </div>
                <div className="text-sm text-white">
                  {data.retraining_recommended ? `Yes (${data.retraining_trigger_reason})` : 'No — rates are below thresholds'}
                </div>
                <div className="text-[12px] text-[#475569] mt-2 font-mono">
                  all-time threshold 15% · recent 7-day threshold 10%
                </div>
                {data.top_override_patterns?.length > 0 && (
                  <ul className="mt-4 text-[12px] text-[#94a3b8] space-y-1">
                    {data.top_override_patterns.map((p: any, idx: number) => (
                      <li key={idx}>{p.from} → {p.to} ({p.count})</li>
                    ))}
                  </ul>
                )}
              </div>
            </motion.div>
          )}
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
