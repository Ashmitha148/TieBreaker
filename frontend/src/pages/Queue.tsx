import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { AlertTriangle, Clock, ArrowRight, Eye, Ban, CheckCircle } from 'lucide-react'

interface QueueItem {
  transaction_id: string
  amount: number
  fraud_probability: number
  recommended_action: string
  impact_score: number
  waiting_seconds: number
}

export default function Queue() {
  const [items, setItems] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetch(`${API_URL}/api/queue`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => { setItems(d.cases || []); setLoading(false) })
      .catch(() => {
        setItems([
          { transaction_id: 'pay_LxK9mN2pQr', amount: 45000, fraud_probability: 0.72, recommended_action: 'REVIEW', impact_score: 92, waiting_seconds: 45 },
          { transaction_id: 'pay_ZxC1bN4vWx', amount: 567000, fraud_probability: 0.48, recommended_action: 'REVIEW', impact_score: 88, waiting_seconds: 120 },
          { transaction_id: 'pay_FgH5iJ0kLm', amount: 150000, fraud_probability: 0.62, recommended_action: 'REVIEW', impact_score: 85, waiting_seconds: 180 },
          { transaction_id: 'pay_QwE4tY1uIo', amount: 34000, fraud_probability: 0.33, recommended_action: 'VERIFY', impact_score: 45, waiting_seconds: 30 },
        ])
        setLoading(false)
      })
  }, [])

  const handleAction = (id: string, _action: string) => {
    setItems(prev => prev.filter(item => item.transaction_id !== id))
  }

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1200px]">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold text-white">Queue Oracle</h1>
              <p className="text-[12px] text-[#475569] font-mono">Priority-ranked review queue</p>
            </div>
            <span className="pill pill-live">{items.length} PENDING</span>
          </div>

          <div className="space-y-3">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="float-card p-4">
                  <div className="shimmer h-16 rounded-lg" />
                </div>
              ))
            ) : (
              items.map((item, i) => (
                <motion.div
                  key={item.transaction_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="float-card p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-[#3395FF]/10 flex items-center justify-center">
                        <AlertTriangle className="w-5 h-5 text-[#3395FF]" />
                      </div>
                      <div>
                        <div className="text-[13px] font-bold text-white font-data">{item.transaction_id}</div>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-[11px] text-[#94a3b8]">₹{item.amount.toLocaleString('en-IN')}</span>
                          <span className="text-[10px] text-[#475569] font-mono">Fraud: {(item.fraud_probability * 100).toFixed(0)}%</span>
                          <span className="text-[10px] text-[#475569] font-mono flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {Math.floor(item.waiting_seconds / 60)}m {item.waiting_seconds % 60}s
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right mr-4">
                        <div className="text-[10px] text-[#475569] uppercase font-bold">Impact Score</div>
                        <div className="text-lg font-bold font-data text-white">{item.impact_score}</div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button onClick={() => handleAction(item.transaction_id, 'ALLOW')} className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-all" title="Allow">
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleAction(item.transaction_id, 'BLOCK')} className="p-2 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-all" title="Block">
                          <Ban className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleAction(item.transaction_id, 'REVIEW')} className="p-2 rounded-lg bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-all" title="Review">
                          <Eye className="w-4 h-4" />
                        </button>
                        <button onClick={() => navigate(`/transaction/${item.transaction_id}`)} className="p-2 rounded-lg bg-white/[0.03] text-[#475569] hover:text-white transition-all" title="Details">
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
