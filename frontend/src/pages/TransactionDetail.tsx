import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useParams, useNavigate } from 'react-router-dom'
import { API_URL } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import TransactionPipeline from '../components/TransactionPipeline'
import DecisionTimeline from '../components/DecisionTimeline'
import WhatIfSimulator from '../components/WhatIfSimulator'
import {
  Zap, Shield, Brain, AlertTriangle, CheckCircle, Clock,
  Activity, ArrowLeft, UserCheck, Ban, Eye
} from 'lucide-react'

export default function TransactionDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [tx, setTx] = useState<any>(null)
  const [overrideAction, setOverrideAction] = useState('')
  const [overrideReason, setOverrideReason] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/api/transactions/${id}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setTx(d))
      .catch(() => {
        setTx({
          transaction_id: id,
          amount: 45000,
          fraud_probability: 0.72,
          fp_probability: 0.35,
          recommended_action: 'REVIEW',
          is_counterintuitive: true,
          velocity_flags: ['High frequency (12 txns/hr)', 'New device fingerprint'],
          shap: { amount: 0.25, velocity: 0.18, device: 0.15, merchant: 0.12, time: 0.10, location: 0.08, history: 0.07, channel: 0.05 },
        })
      })
  }, [id])

  const pipelineSteps = [
    { id: '1', label: 'Payment', detail: 'UPI / Card', status: 'completed' as const, icon: Zap, timestamp: '14:23:01.000' },
    { id: '2', label: 'Velocity', detail: '12 txns/hr', status: 'completed' as const, icon: Activity, timestamp: '14:23:01.120' },
    { id: '3', label: 'Fraud Model', detail: 'prob: 0.72', status: 'completed' as const, icon: Shield, timestamp: '14:23:01.280' },
    { id: '4', label: 'FP Model', detail: 'prob: 0.35', status: 'completed' as const, icon: Brain, timestamp: '14:23:01.310' },
    { id: '5', label: 'Decision', detail: tx?.recommended_action || 'REVIEW', status: 'active' as const, icon: AlertTriangle, timestamp: '14:23:01.340' },
    { id: '6', label: 'Action', detail: 'Queued', status: 'pending' as const, icon: Clock, timestamp: '' },
  ]

  const timelineEvents = [
    { stage: 'Payment Captured', detail: 'UPI transaction initiated', timestamp: '14:23:01.000', duration: '0ms', icon: Zap },
    { stage: 'Velocity Check', detail: '12 transactions in last hour', timestamp: '14:23:01.120', duration: '120ms', icon: Activity },
    { stage: 'Fraud Inference', detail: 'Probability: 0.72 (High Risk)', timestamp: '14:23:01.280', duration: '160ms', icon: Shield },
    { stage: 'FP Inference', detail: 'Probability: 0.35 (Medium)', timestamp: '14:23:01.310', duration: '30ms', icon: Brain },
    { stage: 'Strike Engine', detail: 'Cost-optimized: REVIEW', timestamp: '14:23:01.340', duration: '30ms', icon: AlertTriangle },
  ]

  const handleOverride = () => {
    if (!overrideAction) return
    alert(`Override submitted: ${overrideAction} — ${overrideReason}`)
  }

  if (!tx) return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen flex items-center justify-center">
        <div className="shimmer h-8 w-48 rounded-lg" />
      </div>
    </div>
  )

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1200px]">
          <button onClick={() => navigate('/command')} className="flex items-center gap-1 text-[12px] text-[#94a3b8] hover:text-white mb-4 transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Command Center
          </button>

          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold text-white">{tx.transaction_id}</h1>
              <p className="text-[12px] text-[#475569] font-mono mt-1">Deep dive analysis & override</p>
            </div>
            <span className={`pill ${
              tx.recommended_action === 'ALLOW' ? 'pill-allow' :
              tx.recommended_action === 'BLOCK' ? 'pill-block' :
              tx.recommended_action === 'REVIEW' ? 'pill-review' : 'pill-verify'
            }`}>{tx.recommended_action}</span>
          </div>

          <div className="space-y-5">
            <div>
              <div className="label mb-2">Transaction Pipeline</div>
              <TransactionPipeline steps={pipelineSteps} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-1 space-y-5">
                <div className="float-card p-5">
                  <div className="label mb-4">Decision Timeline</div>
                  <DecisionTimeline events={timelineEvents} />
                </div>

                <div className="float-card p-5">
                  <div className="label mb-4">Velocity Flags</div>
                  <div className="space-y-2">
                    {tx.velocity_flags?.map((flag: string, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-[11px] text-amber-400">
                        <AlertTriangle className="w-3 h-3" /> {flag}
                      </div>
                    )) || <span className="text-[11px] text-[#475569]">No flags</span>}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-1 space-y-5">
                <div className="float-card p-5">
                  <div className="label mb-4">SHAP Explanation</div>
                  <div className="space-y-3">
                    {tx.shap ? Object.entries(tx.shap).sort((a: any, b: any) => b[1] - a[1]).map(([key, val]: [string, any]) => (
                      <div key={key}>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-[#94a3b8] capitalize">{key}</span>
                          <span className="font-data text-[#475569]">{(val * 100).toFixed(0)}%</span>
                        </div>
                        <div className="risk-bar-track">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${val * 100}%` }}
                            transition={{ duration: 0.8 }}
                            className="risk-bar-fill bg-[#3395FF]"
                          />
                        </div>
                      </div>
                    )) : <div className="shimmer h-20 rounded-lg" />}
                  </div>
                </div>

                <div className="float-card p-5">
                  <div className="label mb-4">What-If Simulator</div>
                  <WhatIfSimulator baseAmount={tx.amount} baseLtv={tx.amount * 3} />
                </div>
              </div>

              <div className="lg:col-span-1 space-y-5">
                <div className="float-card p-5">
                  <div className="label mb-4">Transaction Details</div>
                  <div className="space-y-3">
                    {[
                      { label: 'Amount', value: `₹${tx.amount.toLocaleString('en-IN')}` },
                      { label: 'Fraud Probability', value: `${(tx.fraud_probability * 100).toFixed(1)}%` },
                      { label: 'FP Probability', value: `${(tx.fp_probability * 100).toFixed(1)}%` },
                      { label: 'Counterintuitive', value: tx.is_counterintuitive ? 'Yes' : 'No' },
                    ].map((item) => (
                      <div key={item.label} className="flex justify-between items-center py-2 border-b border-white/[0.04]">
                        <span className="text-[11px] text-[#475569]">{item.label}</span>
                        <span className="text-[12px] font-bold font-data text-white">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="float-card p-5">
                  <div className="label mb-4">Analyst Override</div>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { action: 'ALLOW', icon: CheckCircle, color: 'emerald' },
                        { action: 'BLOCK', icon: Ban, color: 'rose' },
                        { action: 'REVIEW', icon: Eye, color: 'amber' },
                        { action: 'VERIFY', icon: UserCheck, color: 'cyan' },
                      ].map((btn) => {
                        const Icon = btn.icon
                        const active = overrideAction === btn.action
                        return (
                          <button
                            key={btn.action}
                            onClick={() => setOverrideAction(btn.action)}
                            className={`flex items-center justify-center gap-1.5 py-2 rounded-lg border text-[11px] font-bold transition-all ${
                              active ? `bg-${btn.color}-500/10 border-${btn.color}-500/30 text-${btn.color}-400` : 'bg-white/[0.02] border-white/[0.06] text-[#475569] hover:text-[#94a3b8]'
                            }`}
                          >
                            <Icon className="w-3.5 h-3.5" /> {btn.action}
                          </button>
                        )
                      })}
                    </div>
                    <textarea
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="Reason for override..."
                      className="w-full bg-[#03040a] border border-white/[0.08] rounded-xl px-3 py-2 text-[12px] text-white placeholder-[#475569] focus:outline-none focus:border-[#3395FF]/40 resize-none h-20"
                    />
                    <button
                      onClick={handleOverride}
                      disabled={!overrideAction}
                      className="w-full py-2.5 bg-gradient-to-r from-[#3395FF] to-[#2563eb] text-white rounded-xl text-[12px] font-bold hover:shadow-lg hover:shadow-[#3395FF]/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Submit Override
                    </button>
                  </div>
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
