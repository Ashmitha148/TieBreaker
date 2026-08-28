import { useEffect, useState } from 'react'
import { Activity, Clock, Cpu } from 'lucide-react'

export default function StatusBar() {
  const [latency, setLatency] = useState(12)
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date())
      setLatency(Math.floor(Math.random() * 20) + 5)
    }, 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#03040a]/90 backdrop-blur-xl border-t border-white/[0.06] px-6 py-2 flex items-center justify-between text-[10px] font-mono text-[#475569]">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-emerald-400" />
          <span>API: {latency}ms</span>
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
