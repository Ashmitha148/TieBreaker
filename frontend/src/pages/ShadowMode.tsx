import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { API_URL } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import {
  Pause, Play, Zap, AlertTriangle,
  TrendingUp, Eye, IndianRupee, Activity,
  ChevronRight, BarChart3, Info, Wifi, WifiOff
} from 'lucide-react'

// ── Types matching backend SSE payload ──
interface TxnData {
  transaction: {
    transaction_id: string
    amount: number
    ltv: number
    merchant_category: string
    fraud_probability: number
    fp_probability: number
    timestamp: string
  }
  prediction: {
    fraud_probability: number
    fp_probability: number
    shap_drivers: { feature: string; impact: number; direction: string }[]
  }
  decision: {
    recommended_action: 'ALLOW' | 'VERIFY' | 'REVIEW' | 'BLOCK'
    baseline_action: 'ALLOW' | 'VERIFY' | 'REVIEW' | 'BLOCK'
    losses: Record<string, number>
    primary_reason: string
    is_counterintuitive: boolean
    confidence_gap: number
  }
  financial_impact: {
    baseline_loss_inr: number
    optimal_loss_inr: number
    savings_inr: number
    ltv_at_risk: number
  }
}

interface StreamPayload {
  type: string
  sequence: number
  data: TxnData
  running_totals: {
    transactions_processed: number
    total_savings_inr: number
    avg_savings_per_tx: number
  }
  timestamp: string
}

const ACTION_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  ALLOW:   { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', label: 'ALLOW' },
  VERIFY:  { bg: 'bg-cyan-500/10',   text: 'text-cyan-400',   border: 'border-cyan-500/20',   label: 'VERIFY' },
  REVIEW:  { bg: 'bg-amber-500/10',  text: 'text-amber-400',  border: 'border-amber-500/20',  label: 'REVIEW' },
  BLOCK:   { bg: 'bg-rose-500/10',   text: 'text-rose-400',   border: 'border-rose-500/20',   label: 'BLOCK' },
}

const MERCHANT_COLORS: Record<string, string> = {
  Retail: '#3395FF',
  SaaS: '#a855f7',
  B2B: '#10b981',
  Food: '#f59e0b',
  Travel: '#f43f5e',
  EdTech: '#06b6d4',
}

export default function ShadowMode() {
  const [transactions, setTransactions] = useState<StreamPayload[]>([])
  const [selectedTx, setSelectedTx] = useState<StreamPayload | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [counterintuitiveCount, setCounterintuitiveCount] = useState(0)
  const eventSourceRef = useRef<EventSource | null>(null)

  // Running totals from latest SSE event
  const totals = useMemo(() => {
    if (transactions.length === 0) return { transactions_processed: 0, total_savings_inr: 0, avg_savings_per_tx: 0 }
    return transactions[0].running_totals
  }, [transactions])

  // Merchant breakdown computed from visible history
  const merchantStats = useMemo(() => {
    const map: Record<string, { count: number; savings: number }> = {}
    transactions.forEach((t) => {
      const cat = t.data.transaction.merchant_category || 'Other'
      if (!map[cat]) map[cat] = { count: 0, savings: 0 }
      map[cat].count += 1
      map[cat].savings += t.data.financial_impact.savings_inr
    })
    return Object.entries(map)
      .map(([name, stats]) => ({ name, ...stats }))
      .sort((a, b) => b.savings - a.savings)
  }, [transactions])

  const connect = useCallback(() => {
    if (eventSourceRef.current) return
    const es = new EventSource(`${API_URL}/api/stream/transactions?delay_ms=1800`)
    eventSourceRef.current = es

    es.onopen = () => setIsConnected(true)

    es.onmessage = (e) => {
      try {
        const payload: StreamPayload = JSON.parse(e.data)
        if (payload.type === 'transaction') {
          setTransactions((prev) => {
            const next = [payload, ...prev].slice(0, 60)
            return next
          })
          setSelectedTx((prev) => prev || payload) // auto-select first
          if (payload.data.decision.is_counterintuitive) {
            setCounterintuitiveCount((c) => c + 1)
          }
        }
      } catch {
        // ignore malformed
      }
    }

    es.onerror = () => {
      setIsConnected(false)
      es.close()
      eventSourceRef.current = null
      setTimeout(() => {
        if (!isPaused) connect()
      }, 3000)
    }
  }, [isPaused])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsConnected(false)
  }, [])

  useEffect(() => {
    if (!isPaused) connect()
    return () => disconnect()
  }, [isPaused, connect, disconnect])

  const togglePause = () => setIsPaused((p) => !p)

  

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        {/* Header */}
        <div className="pt-6 pb-4 px-6 max-w-[1600px]">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-xl font-bold text-white tracking-tight">Shadow Mode</h1>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-[10px] text-[#64748b]">
                  <Info className="w-3 h-3" />
                  Simulated on synthetic Indian payment data
                </span>
              </div>
              <p className="text-[12px] text-[#475569] font-mono">
                Live side-by-side: Traditional threshold system vs TieBreaker cost optimization
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[11px] font-mono ${
                isConnected
                  ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-400'
                  : 'border-rose-500/20 bg-rose-500/5 text-rose-400'
              }`}>
                {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                {isConnected ? 'STREAM LIVE' : 'RECONNECTING...'}
              </div>

              <button
                onClick={togglePause}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[11px] font-bold transition-all ${
                  isPaused
                    ? 'border-[#3395FF]/30 bg-[#3395FF]/10 text-[#3395FF] hover:bg-[#3395FF]/20'
                    : 'border-white/[0.08] bg-white/[0.03] text-[#94a3b8] hover:bg-white/[0.06]'
                }`}
              >
                {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                {isPaused ? 'RESUME' : 'PAUSE'}
              </button>
            </div>
          </div>
        </div>

        {/* Top Stats */}
        <div className="px-6 max-w-[1600px]">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              icon={Activity}
              label="Transactions Processed"
              value={totals.transactions_processed}
              prefix=""
              color="text-[#3395FF]"
            />
            <StatCard
              icon={IndianRupee}
              label="Total Savings"
              value={totals.total_savings_inr}
              prefix="₹"
              color="text-emerald-400"
              isCurrency
            />
            <StatCard
              icon={AlertTriangle}
              label="Counterintuitive Decisions"
              value={counterintuitiveCount}
              prefix=""
              color="text-amber-400"
            />
            <StatCard
              icon={TrendingUp}
              label="Avg Savings / TX"
              value={totals.avg_savings_per_tx}
              prefix="₹"
              color="text-[#a855f7]"
              isCurrency
            />
          </div>
        </div>

        {/* Main Content */}
        <div className="px-6 max-w-[1600px] grid grid-cols-1 xl:grid-cols-5 gap-5">
          {/* Left: Transaction Feed */}
          <div className="xl:col-span-3 space-y-4">
            <div className="flex items-center justify-between mb-1">
              <span className="label">Live Transaction Feed</span>
              <span className="text-[10px] text-[#475569] font-mono">{transactions.length} visible</span>
            </div>

            <div className="space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
              <AnimatePresence initial={false}>
                {transactions.map((t) => (
                  <TxCard
                    key={`${t.sequence}-${t.data.transaction.transaction_id}`}
                    payload={t}
                    isSelected={selectedTx?.sequence === t.sequence}
                    onClick={() => setSelectedTx(t)}
                  />
                ))}
              </AnimatePresence>

              {transactions.length === 0 && (
                <div className="float-card p-8 text-center">
                  <Activity className="w-8 h-8 text-[#475569] mx-auto mb-3 animate-pulse" />
                  <p className="text-[13px] text-[#64748b]">Waiting for transactions...</p>
                  <p className="text-[11px] text-[#475569] font-mono mt-1">
                    Connect to {API_URL}/api/stream/transactions
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right: Detail Comparison */}
          <div className="xl:col-span-2 space-y-4">
            <div className="label mb-1">Decision Comparison</div>

            {selectedTx ? (
              <DecisionDetail payload={selectedTx} />
            ) : (
              <div className="float-card p-8 text-center">
                <Eye className="w-8 h-8 text-[#475569] mx-auto mb-3" />
                <p className="text-[13px] text-[#64748b]">Select a transaction to compare</p>
              </div>
            )}

            {/* Merchant Breakdown */}
            <div className="float-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-[#475569]" />
                <span className="label">Savings by Merchant Category</span>
              </div>

              {merchantStats.length === 0 ? (
                <p className="text-[12px] text-[#475569] text-center py-4">No data yet</p>
              ) : (
                <div className="space-y-3">
                  {merchantStats.map((m) => {
                    const maxSavings = Math.max(...merchantStats.map((x) => x.savings))
                    const pct = maxSavings > 0 ? (m.savings / maxSavings) * 100 : 0
                    const color = MERCHANT_COLORS[m.name] || '#3395FF'
                    return (
                      <div key={m.name}>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-[#94a3b8]">{m.name}</span>
                          <span className="font-data text-[#475569]">
                            ₹{Math.round(m.savings).toLocaleString('en-IN')} ({m.count} tx)
                          </span>
                        </div>
                        <div className="risk-bar-track h-1.5">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.6 }}
                            className="h-full rounded-full"
                            style={{ backgroundColor: color }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <StatusBar />
    </div>
  )
}

// ── Sub-components ──

function StatCard({ icon: Icon, label, value, color, isCurrency }: any) {
  const display = isCurrency
    ? `₹${Math.round(value).toLocaleString('en-IN')}`
    : value.toLocaleString('en-IN')

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="float-card p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div className="text-2xl font-bold text-white font-data">{display}</div>
      <div className="text-[11px] text-[#475569] mt-1">{label}</div>
    </motion.div>
  )
}

function TxCard({ payload, isSelected, onClick }: { payload: StreamPayload; isSelected: boolean; onClick: () => void }) {
  const { transaction, decision, financial_impact } = payload.data
  const baselineStyle = ACTION_STYLES[decision.baseline_action] || ACTION_STYLES.BLOCK
  const tiebreakerStyle = ACTION_STYLES[decision.recommended_action] || ACTION_STYLES.REVIEW

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 40, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -40, scale: 0.95 }}
      transition={{ duration: 0.35 }}
      onClick={onClick}
      className={`float-card p-4 cursor-pointer transition-all ${
        isSelected ? 'ring-1 ring-[#3395FF]/40' : ''
      } ${decision.is_counterintuitive ? 'border-l-2 border-l-amber-400' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-data text-[11px] text-white truncate">{transaction.transaction_id}</span>
            <span className="text-[9px] text-[#475569] font-mono">
              {new Date(transaction.timestamp).toLocaleTimeString('en-IN')}
            </span>
            {decision.is_counterintuitive && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[9px] font-bold border border-amber-500/20">
                <AlertTriangle className="w-2.5 h-2.5" />
                Counter
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mb-2">
            <span className="font-data text-[13px] text-white font-bold">
              ₹{transaction.amount.toLocaleString('en-IN')}
            </span>
            <span className="text-[10px] text-[#64748b] bg-white/[0.04] px-1.5 py-0.5 rounded">
              {transaction.merchant_category}
            </span>
            <span className="text-[10px] text-[#475569] font-mono">
              LTV ₹{Math.round(transaction.ltv).toLocaleString('en-IN')}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="risk-bar-track w-24">
              <div
                className={`risk-bar-fill ${
                  transaction.fraud_probability > 0.7 ? 'bg-rose-500' :
                  transaction.fraud_probability > 0.4 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${transaction.fraud_probability * 100}%` }}
              />
            </div>
            <span className="font-data text-[10px] text-[#64748b]">
              {(transaction.fraud_probability * 100).toFixed(0)}% fraud
            </span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <span className={`text-[9px] px-1.5 py-0.5 rounded border ${baselineStyle.border} ${baselineStyle.bg} ${baselineStyle.text}`}>
              Old: {baselineStyle.label}
            </span>
            <ChevronRight className="w-3 h-3 text-[#475569]" />
            <span className={`text-[9px] px-1.5 py-0.5 rounded border ${tiebreakerStyle.border} ${tiebreakerStyle.bg} ${tiebreakerStyle.text}`}>
              TB: {tiebreakerStyle.label}
            </span>
          </div>
          {financial_impact.savings_inr > 0 && (
            <span className="text-[11px] font-bold text-emerald-400 font-data">
              +₹{Math.round(financial_impact.savings_inr).toLocaleString('en-IN')} saved
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

function DecisionDetail({ payload }: { payload: StreamPayload }) {
  const { transaction, decision, financial_impact, prediction } = payload.data
  const baselineStyle = ACTION_STYLES[decision.baseline_action] || ACTION_STYLES.BLOCK
  const tiebreakerStyle = ACTION_STYLES[decision.recommended_action] || ACTION_STYLES.REVIEW

  return (
    <div className="float-card p-5 space-y-5">
      {/* Big Savings Headline */}
      <div className="text-center pb-4 border-b border-white/[0.06]">
        <div className="text-[11px] text-[#475569] font-mono mb-1">FINANCIAL IMPACT</div>
        <motion.div
          key={financial_impact.savings_inr}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-3xl font-bold text-emerald-400 font-data"
        >
          ₹{Math.round(financial_impact.savings_inr).toLocaleString('en-IN')}
        </motion.div>
        <div className="text-[12px] text-[#64748b] mt-1">saved vs traditional threshold system</div>
      </div>

      {/* Side-by-Side */}
      <div className="grid grid-cols-2 gap-3">
        <div className={`rounded-xl border ${baselineStyle.border} ${baselineStyle.bg} p-4`}>
          <div className="text-[10px] text-[#475569] font-mono mb-2">TRADITIONAL SYSTEM</div>
          <div className={`text-lg font-bold ${baselineStyle.text}`}>{baselineStyle.label}</div>
          <div className="text-[11px] text-[#64748b] mt-1">
            Loss: ₹{Math.round(financial_impact.baseline_loss_inr).toLocaleString('en-IN')}
          </div>
        </div>

        <div className={`rounded-xl border ${tiebreakerStyle.border} ${tiebreakerStyle.bg} p-4`}>
          <div className="text-[10px] text-[#475569] font-mono mb-2">TIEBREAKER</div>
          <div className={`text-lg font-bold ${tiebreakerStyle.text}`}>{tiebreakerStyle.label}</div>
          <div className="text-[11px] text-[#64748b] mt-1">
            Loss: ₹{Math.round(financial_impact.optimal_loss_inr).toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Reason */}
      <div className="bg-white/[0.02] rounded-lg p-3 border border-white/[0.06]">
        <div className="flex items-start gap-2">
          <Zap className="w-3.5 h-3.5 text-[#3395FF] mt-0.5 shrink-0" />
          <p className="text-[12px] text-[#94a3b8] leading-relaxed">{decision.primary_reason}</p>
        </div>
      </div>

      {/* Loss Breakdown */}
      <div>
        <div className="text-[10px] text-[#475569] font-mono mb-2">EXPECTED LOSS BREAKDOWN</div>
        <div className="space-y-1.5">
          {Object.entries(decision.losses).map(([action, loss]) => (
            <div key={action} className="flex items-center justify-between text-[11px]">
              <span className="text-[#64748b]">{action}</span>
              <span className={`font-data ${
                action === decision.recommended_action ? 'text-emerald-400 font-bold' : 'text-[#475569]'
              }`}>
                ₹{Math.round(loss).toLocaleString('en-IN')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* SHAP Drivers */}
      {prediction.shap_drivers && prediction.shap_drivers.length > 0 && (
        <div>
          <div className="text-[10px] text-[#475569] font-mono mb-2">TOP RISK DRIVERS</div>
          <div className="space-y-2">
            {prediction.shap_drivers.map((d, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${d.direction === 'increases' ? 'bg-rose-400' : 'bg-emerald-400'}`} />
                <span className="text-[11px] text-[#94a3b8] flex-1">{d.feature.replace(/_/g, ' ')}</span>
                <span className={`text-[11px] font-data ${d.direction === 'increases' ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {d.direction === 'increases' ? '+' : '-'}{Math.abs(d.impact).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transaction Meta */}
      <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-[#475569] font-mono">
        <span>#{transaction.transaction_id}</span>
        <span>Confidence gap: ₹{decision.confidence_gap.toLocaleString('en-IN')}</span>
      </div>
    </div>
  )
}