import { useEffect, useState } from 'react'
import { Activity, Clock, Cpu } from 'lucide-react'
import { API_URL } from '../config'

type BackendState = 'checking' | 'ok' | 'degraded' | 'offline'

export default function StatusBar() {
  const [state, setState] = useState<BackendState>('checking')
  const [latency, setLatency] = useState<number | null>(null)
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const clock = setInterval(() => setTime(new Date()), 1000)
    let alive = true
    const ping = async () => {
      const t0 = performance.now()
      try {
        const res = await fetch(`${API_URL}/health`, { cache: 'no-store' })
        if (!alive) return
        if (!res.ok) { setState('offline'); setLatency(null); return }
        const body = await res.json()
        setLatency(Math.round(performance.now() - t0))
        setState(body.status === 'ok' ? 'ok' : 'degraded')
      } catch {
        if (alive) { setState('offline'); setLatency(null) }
      }
    }
    ping()
    const health = setInterval(ping, 15000)
    return () => { alive = false; clearInterval(clock); clearInterval(health) }
  }, [])

  const dotColor = { checking: 'text-slate-500', ok: 'text-emerald-400',
    degraded: 'text-amber-400', offline: 'text-red-400' }[state]
  const label = { checking: 'checking…', ok: `${latency}ms`,
    degraded: `${latency}ms · degraded`, offline: 'BACKEND OFFLINE' }[state]

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#03040a]/90 backdrop-blur-xl border-t border-white/[0.06] px-6 py-2 flex items-center justify-between text-[10px] font-mono text-[#475569]">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Activity className={`w-3 h-3 ${dotColor}`} />
          <span>API: {label}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3 h-3 text-[#3395FF]" />
          <span>Model v2.0.0</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <Clock className="w-3 h-3" />
        <span>{time.toLocaleTimeString('en-IN', { hour12: false })} IST</span>
      </div>
    </div>
  )
}