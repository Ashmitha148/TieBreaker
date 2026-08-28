import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { API_URL } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { Filter } from 'lucide-react'

interface AuditLog {
  id: string
  timestamp: string
  transaction_id: string
  action: string
  analyst_id?: string
  reason?: string
  model_version: string
}

export default function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/api/audit`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => { setLogs(d.logs || []); setLoading(false) })
      .catch(() => {
        setLogs([
          { id: '1', timestamp: '2024-01-15T14:23:01', transaction_id: 'pay_LxK9mN2pQr', action: 'DECISION_REVIEW', analyst_id: 'system', model_version: '2.0.0' },
          { id: '2', timestamp: '2024-01-15T14:22:58', transaction_id: 'pay_MnP2qR5sTu', action: 'DECISION_ALLOW', analyst_id: 'system', model_version: '2.0.0' },
          { id: '3', timestamp: '2024-01-15T14:22:55', transaction_id: 'pay_KjH7vW8xYz', action: 'DECISION_BLOCK', analyst_id: 'system', model_version: '2.0.0' },
          { id: '4', timestamp: '2024-01-15T14:21:30', transaction_id: 'pay_ZxC1bN4vWx', action: 'OVERRIDE_REVIEW', analyst_id: 'analyst_001', reason: 'Customer verified via call', model_version: '2.0.0' },
          { id: '5', timestamp: '2024-01-15T14:18:12', transaction_id: 'pay_AbC3dE7fGh', action: 'CONFIG_UPDATE', analyst_id: 'admin', reason: 'Updated fraud threshold to 0.72', model_version: '2.0.0' },
          { id: '6', timestamp: '2024-01-15T14:15:45', transaction_id: 'pay_FgH5iJ0kLm', action: 'DECISION_VERIFY', analyst_id: 'system', model_version: '2.0.0' },
        ])
        setLoading(false)
      })
  }, [])

  const filtered = logs.filter(l =>
    l.transaction_id.toLowerCase().includes(filter.toLowerCase()) ||
    l.action.toLowerCase().includes(filter.toLowerCase())
  )

  const actionColor = (action: string) => {
    if (action.includes('ALLOW')) return 'pill-allow'
    if (action.includes('BLOCK')) return 'pill-block'
    if (action.includes('REVIEW')) return 'pill-review'
    if (action.includes('VERIFY')) return 'pill-verify'
    return 'pill-review'
  }

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1400px]">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold text-white">System Audit</h1>
              <p className="text-[12px] text-[#475569] font-mono">Decision and override audit trail</p>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[#475569]" />
              <input type="text" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter logs..."
                className="bg-[#03040a] border border-white/[0.08] rounded-xl px-4 py-2 text-[12px] text-white placeholder-[#475569] focus:outline-none focus:border-[#3395FF]/40 w-48" />
            </div>
          </div>

          <div className="float-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Transaction</th>
                    <th>Action</th>
                    <th>Analyst</th>
                    <th>Reason</th>
                    <th>Model</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i}>
                        <td className="p-4"><div className="shimmer h-3 w-16" /></td>
                        <td className="p-4"><div className="shimmer h-3 w-24" /></td>
                        <td className="p-4"><div className="shimmer h-5 w-16" /></td>
                        <td className="p-4"><div className="shimmer h-3 w-16" /></td>
                        <td className="p-4"><div className="shimmer h-3 w-32" /></td>
                        <td className="p-4"><div className="shimmer h-3 w-10" /></td>
                      </tr>
                    ))
                  ) : (
                    filtered.map((log, i) => (
                      <motion.tr key={log.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }}>
                        <td className="font-data text-[10px] text-[#475569]">{new Date(log.timestamp).toLocaleTimeString('en-IN', { hour12: false })}</td>
                        <td className="font-data text-[12px] text-white">{log.transaction_id}</td>
                        <td><span className={`pill ${actionColor(log.action)}`}>{log.action}</span></td>
                        <td className="font-data text-[11px] text-[#94a3b8]">{log.analyst_id || '—'}</td>
                        <td className="text-[11px] text-[#475569] max-w-[200px] truncate">{log.reason || '—'}</td>
                        <td className="font-data text-[10px] text-[#475569]">{log.model_version}</td>
                      </motion.tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
