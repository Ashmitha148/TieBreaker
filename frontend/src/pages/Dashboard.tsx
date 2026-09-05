import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { API_URL, apiHeaders } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import TransactionPipeline from '../components/TransactionPipeline'
import LiveTicker from '../components/LiveTicker'
import { Activity, Shield, Clock, AlertTriangle, Zap, Brain } from 'lucide-react'

interface Txn {
  transaction_id: string
  amount: number
  fraud_probability: number
  recommended_action: string
  is_counterintuitive: boolean
  created_at: string
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null)
  const [txns, setTxns] = useState<Txn[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTx, setSelectedTx] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/api/metrics`, { headers: apiHeaders() })
      fetch(`${API_URL}/api/queue?limit=10`, { headers: apiHeaders() }).then(r => r.ok ? r.json() : Promise.reject())
    ])
      .then(([m, q]) => {
        setMetrics(m)
        setTxns(q.cases || [])
        setLoading(false)
      })
      .catch(() => {
        setTxns([
          { transaction_id: 'pay_LxK9mN2pQr', amount: 45000, fraud_probability: 0.72, recommended_action: 'REVIEW', is_counterintuitive: true, created_at: '2024-01-15T14:23:01' },
          { transaction_id: 'pay_MnP2qR5sTu', amount: 120000, fraud_probability: 0.15, recommended_action: 'ALLOW', is_counterintuitive: false, created_at: '2024-01-15T14:22:58' },
          { transaction_id: 'pay_KjH7vW8xYz', amount: 89000, fraud_probability: 0.91, recommended_action: 'BLOCK', is_counterintuitive: false, created_at: '2024-01-15T14:22:55' },
          { transaction_id: 'pay_QwE4tY1uIo', amount: 34000, fraud_probability: 0.33, recommended_action: 'VERIFY', is_counterintuitive: false, created_at: '2024-01-15T14:22:52' },
          { transaction_id: 'pay_ZxC1bN4vWx', amount: 567000, fraud_probability: 0.48, recommended_action: 'REVIEW', is_counterintuitive: false, created_at: '2024-01-15T14:22:49' },
          { transaction_id: 'pay_AbC3dE7fGh', amount: 22000, fraud_probability: 0.08, recommended_action: 'ALLOW', is_counterintuitive: false, created_at: '2024-01-15T14:22:46' },
          { transaction_id: 'pay_FgH5iJ0kLm', amount: 150000, fraud_probability: 0.62, recommended_action: 'REVIEW', is_counterintuitive: true, created_at: '2024-01-15T14:22:43' },
          { transaction_id: 'pay_KlM6nO9pQr', amount: 7800, fraud_probability: 0.88, recommended_action: 'BLOCK', is_counterintuitive: false, created_at: '2024-01-15T14:22:40' },
        ])
        setLoading(false)
      })
  }, [])

  const pipelineSteps = selectedTx ? [
    { id: '1', label: 'Payment', detail: 'UPI / Card', status: 'completed' as const, icon: Zap, timestamp: '14:23:01.000' },
    { id: '2', label: 'Velocity', detail: '12 txns/hr', status: 'completed' as const, icon: Activity, timestamp: '14:23:01.120' },
    { id: '3', label: 'Fraud Model', detail: 'prob: 0.72', status: 'completed' as const, icon: Shield, timestamp: '14:23:01.280' },
    { id: '4', label: 'FP Model', detail: 'prob: 0.35', status: 'completed' as const, icon: Brain, timestamp: '14:23:01.310' },
    { id: '5', label: 'Decision', detail: 'REVIEW', status: 'active' as const, icon: AlertTriangle, timestamp: '14:23:01.340' },
    { id: '6', label: 'Action', detail: 'Queued', status: 'pending' as const, icon: Clock, timestamp: '' },
  ] : [
    { id: '1', label: 'Payment', detail: 'Waiting...', status: 'pending' as const, icon: Zap },
    { id: '2', label: 'Velocity', detail: '—', status: 'pending' as const, icon: Activity },
    { id: '3', label: 'Fraud Model', detail: '—', status: 'pending' as const, icon: Shield },
    { id: '4', label: 'FP Model', detail: '—', status: 'pending' as const, icon: Brain },
    { id: '5', label: 'Decision', detail: '—', status: 'pending' as const, icon: AlertTriangle },
    { id: '6', label: 'Action', detail: '—', status: 'pending' as const, icon: Clock },
  ]

  const stats = [
    { label: 'Total Decisions', value: metrics?.system_stats?.total_decisions ?? 0, prefix: '', icon: Activity },
    { label: 'Fraud Prevented', value: metrics?.financial_impact?.fraud_loss_prevented ?? 0, prefix: '₹', icon: Shield },
    { label: 'Override Rate', value: metrics?.system_stats?.override_rate ?? 0, prefix: '', suffix: '%', decimals: 1, icon: AlertTriangle },
    { label: 'Avg Review', value: metrics?.queue_stats?.avg_review_time_minutes ?? 0, prefix: '', suffix: 'm', decimals: 1, icon: Clock },
  ]

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <LiveTicker />
        <div className="pt-6 pb-8 px-6 max-w-[1400px]">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Risk Command Center</h1>
              <p className="text-[12px] text-[#475569] font-mono mt-1">
                {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} • IST
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="pill pill-live">LIVE</span>
              <span className="text-[10px] text-[#475569] font-mono">v2.0.0</span>
            </div>
          </div>

          <div className="mb-6">
            <div className="label mb-2">
              Transaction Pipeline {selectedTx && <span className="text-[#3395FF] font-mono ml-2">{selectedTx}</span>}
            </div>
            <TransactionPipeline steps={pipelineSteps} />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {stats.map((s, i) => {
              const Icon = s.icon
              return (
                <motion.div
                  key={s.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="float-card p-5"
                >
                  <div className="flex items-center justify-between mb-3">
                    <Icon className="w-4 h-4 text-[#475569]" />
                  </div>
                  <div className="text-2xl font-bold text-white font-data">
                    {s.prefix}{s.value.toLocaleString('en-IN', { minimumFractionDigits: s.decimals || 0, maximumFractionDigits: s.decimals || 0 })}{s.suffix}
                  </div>
                  <div className="text-[11px] text-[#475569] mt-1">{s.label}</div>
                </motion.div>
              )
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 float-card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                <span className="label">Live Transactions</span>
                <span className="text-[11px] text-[#475569] font-mono">{txns.length} records</span>
              </div>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Transaction</th>
                      <th className="text-right">Amount</th>
                      <th>Fraud</th>
                      <th>Action</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <tr key={i}>
                          <td className="p-4"><div className="shimmer h-3 w-28" /></td>
                          <td className="p-4"><div className="shimmer h-3 w-16 ml-auto" /></td>
                          <td className="p-4"><div className="shimmer h-2 w-20" /></td>
                          <td className="p-4"><div className="shimmer h-5 w-14" /></td>
                          <td className="p-4"><div className="shimmer h-3 w-10" /></td>
                        </tr>
                      ))
                    ) : (
                      txns.map((t, i) => (
                        <motion.tr
                          key={t.transaction_id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: i * 0.03 }}
                          className="cursor-pointer"
                          onClick={() => {
                            setSelectedTx(t.transaction_id)
                            setTimeout(() => navigate(`/transaction/${t.transaction_id}`), 600)
                          }}
                        >
                          <td className="font-data text-[12px] text-white">{t.transaction_id}</td>
                          <td className="font-data text-[12px] text-white text-right">₹{t.amount.toLocaleString('en-IN')}</td>
                          <td>
                            <div className="flex items-center gap-2.5">
                              <div className="risk-bar-track w-20">
                                <div
                                  className={`risk-bar-fill ${t.fraud_probability > 0.7 ? 'bg-rose-500' : t.fraud_probability > 0.4 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                  style={{ width: `${t.fraud_probability * 100}%` }}
                                />
                              </div>
                              <span className="font-data text-[10px] text-[#64748b]">{(t.fraud_probability * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                          <td>
                            <span className={`pill ${
                              t.recommended_action === 'ALLOW' ? 'pill-allow' :
                              t.recommended_action === 'REVIEW' ? 'pill-review' :
                              t.recommended_action === 'BLOCK' ? 'pill-block' : 'pill-review'
                            }`}>
                              {t.recommended_action}
                            </span>
                          </td>
                          <td>
                            {t.is_counterintuitive && (
                              <span className="text-[11px] text-amber-400 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" /> Counter
                              </span>
                            )}
                          </td>
                        </motion.tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-5">
              <div className="float-card p-5">
                <span className="label block mb-4">Model Performance</span>
                {metrics?.model_performance ? (
                  <div className="space-y-4">
                    {Object.entries(metrics.model_performance).map(([key, val]: [string, any]) => (
                      <div key={key}>
                        <div className="flex justify-between text-[12px] mb-1.5">
                          <span className="text-[#94a3b8] capitalize">{key.replace('_', ' ')}</span>
                          <span className="font-data text-[11px] text-[#475569]">F1: {(val.f1 * 100).toFixed(0)}%</span>
                        </div>
                        <div className="risk-bar-track">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(val.f1 || 0.8) * 100}%` }}
                            transition={{ duration: 1, delay: 0.3 }}
                            className="risk-bar-fill bg-gradient-to-r from-[#3395FF] to-[#a855f7]"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="shimmer h-7 rounded-lg" />
                    <div className="shimmer h-7 rounded-lg" />
                  </div>
                )}
              </div>

              <div className="float-card p-5">
                <span className="label block mb-4">Navigate</span>
                <div className="space-y-1">
                  {[
                    { label: 'Queue Oracle', path: '/queue' },
                    { label: 'Override Learning', path: '/learning' },
                    { label: 'System Audit', path: '/audit' },
                  ].map((a) => (
                    <button
                      key={a.label}
                      onClick={() => navigate(a.path)}
                      className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors group"
                    >
                      <span className="text-[12px] text-[#94a3b8] group-hover:text-white transition-colors">{a.label}</span>
                      <span className="text-[#475569] group-hover:text-white transition-colors">→</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}