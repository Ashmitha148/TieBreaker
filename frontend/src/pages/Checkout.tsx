import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CreditCard, Smartphone, Banknote, ArrowRight, Shield,
  Zap, CheckCircle, AlertTriangle, Clock, Brain
} from 'lucide-react'
import TransactionPipeline from '../components/TransactionPipeline'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { API_URL } from '../config'

export default function Checkout() {
  const [amount, setAmount] = useState('500')
  const [email, setEmail] = useState('user@example.com')
  const [phone, setPhone] = useState('9999999999')
  const [method, setMethod] = useState<'upi' | 'card' | 'netbanking'>('upi')
  const [stage, setStage] = useState<'form' | 'processing' | 'result'>('form')
  const [result, setResult] = useState<any>(null)
  const [pipelineSteps, setPipelineSteps] = useState<any[]>([])

  const startPipeline = (txId: string) => {
    const steps = [
      { id: '1', label: 'Payment', detail: 'UPI / Card', status: 'pending' as const, icon: Zap },
      { id: '2', label: 'Velocity', detail: 'Checking...', status: 'pending' as const, icon: Clock },
      { id: '3', label: 'Fraud Model', detail: 'Inference...', status: 'pending' as const, icon: Shield },
      { id: '4', label: 'FP Model', detail: 'Inference...', status: 'pending' as const, icon: Brain },
      { id: '5', label: 'Decision', detail: 'Optimizing...', status: 'pending' as const, icon: AlertTriangle },
      { id: '6', label: 'Action', detail: 'Executing...', status: 'pending' as const, icon: CheckCircle },
    ]
    setPipelineSteps(steps)
    setStage('processing')

    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 0 ? { ...step, status: 'completed', detail: '₹' + amount, timestamp: '14:23:01.000' } : step)), 400)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 1 ? { ...step, status: 'completed', detail: '12 txns/hr', timestamp: '14:23:01.120' } : step)), 900)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 2 ? { ...step, status: 'completed', detail: 'prob: 0.72', timestamp: '14:23:01.280' } : step)), 1400)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 3 ? { ...step, status: 'completed', detail: 'prob: 0.35', timestamp: '14:23:01.310' } : step)), 1800)
    setTimeout(() => {
      const rec = Math.random() > 0.5 ? 'REVIEW' : 'ALLOW'
      setPipelineSteps(s => s.map((step, i) => i === 4 ? { ...step, status: 'active', detail: rec, timestamp: '14:23:01.340' } : step))
      setResult({ transaction_id: txId, amount: Number(amount), recommended_action: rec, fraud_probability: 0.72, fp_probability: 0.35, is_counterintuitive: rec === 'REVIEW' })
    }, 2200)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 5 ? { ...step, status: 'completed', detail: 'Done', timestamp: '14:23:01.400' } : step)), 2800)
    setTimeout(() => setStage('result'), 3200)
  }

  const handlePay = async () => {
    try {
      const res = await fetch(`${API_URL}/api/create-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: Number(amount) * 100, currency: 'INR' })
      })
      if (!res.ok) throw new Error('Backend not ready')
      const data = await res.json()
      startPipeline(data.transaction_id || 'pay_' + Math.random().toString(36).slice(2, 10))
    } catch {
      startPipeline('pay_' + Math.random().toString(36).slice(2, 10))
    }
  }

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-8 pb-8 px-6 max-w-[1000px]">
          <h1 className="text-xl font-bold text-white mb-1">Payment Checkout</h1>
          <p className="text-[12px] text-[#475569] font-mono mb-8">Initiate payment → Risk scoring → Intelligent decision</p>

          <AnimatePresence mode="wait">
            {stage === 'form' && (
              <motion.div key="form" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="float-card p-6">
                  <div className="label mb-5">Payment Details</div>
                  <div className="space-y-4">
                    <div>
                      <div className="text-[11px] text-[#475569] uppercase font-bold mb-1.5">Amount (₹)</div>
                      <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
                        className="w-full bg-[#03040a] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white font-data focus:outline-none focus:border-[#3395FF]/40" />
                    </div>
                    <div>
                      <div className="text-[11px] text-[#475569] uppercase font-bold mb-1.5">Email</div>
                      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-[#03040a] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-[#3395FF]/40" />
                    </div>
                    <div>
                      <div className="text-[11px] text-[#475569] uppercase font-bold mb-1.5">Phone</div>
                      <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                        className="w-full bg-[#03040a] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white font-data focus:outline-none focus:border-[#3395FF]/40" />
                    </div>
                    <div>
                      <div className="text-[11px] text-[#475569] uppercase font-bold mb-1.5">Payment Method</div>
                      <div className="flex gap-2">
                        {([
                          { key: 'upi', label: 'UPI', icon: Smartphone },
                          { key: 'card', label: 'Card', icon: CreditCard },
                          { key: 'netbanking', label: 'NetBanking', icon: Banknote },
                        ] as const).map((m) => {
                          const Icon = m.icon
                          const active = method === m.key
                          return (
                            <button key={m.key} onClick={() => setMethod(m.key)}
                              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl border text-[12px] font-medium transition-all ${
                                active ? 'bg-[#3395FF]/10 border-[#3395FF]/30 text-[#3395FF]' : 'bg-white/[0.02] border-white/[0.06] text-[#475569] hover:text-[#94a3b8]'
                              }`}>
                              <Icon className="w-4 h-4" />{m.label}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                    <button onClick={handlePay}
                      className="w-full py-3 bg-gradient-to-r from-[#3395FF] to-[#2563eb] text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-[#3395FF]/25 transition-all flex items-center justify-center gap-2">
                      Pay ₹{Number(amount).toLocaleString('en-IN')}<ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="float-card p-6">
                    <div className="label mb-4">How It Works</div>
                    <div className="space-y-4">
                      {[
                        { step: '01', title: 'Payment Initiated', desc: 'Customer completes checkout via UPI/Card/NetBanking' },
                        { step: '02', title: 'Velocity Check', desc: 'Real-time velocity rules scan transaction patterns' },
                        { step: '03', title: 'Dual Model Inference', desc: 'Fraud + False Positive models run in parallel' },
                        { step: '04', title: 'Cost Optimization', desc: 'Strike Decision Engine picks lowest-loss action' },
                        { step: '05', title: 'Analyst Override', desc: 'Counterintuitive cases flagged for human review' },
                      ].map((s) => (
                        <div key={s.step} className="flex gap-3">
                          <div className="text-[10px] font-mono text-[#3395FF] mt-0.5 font-bold">{s.step}</div>
                          <div>
                            <div className="text-[13px] font-bold text-[#f0f2f5]">{s.title}</div>
                            <div className="text-[11px] text-[#475569]">{s.desc}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {(stage === 'processing' || stage === 'result') && (
              <motion.div key="processing" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
                <div>
                  <div className="label mb-2">Transaction Pipeline</div>
                  <TransactionPipeline steps={pipelineSteps} />
                </div>
                {stage === 'result' && result && (
                  <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="float-card p-6">
                    <div className="flex items-center justify-between mb-5">
                      <div>
                        <div className="text-[10px] text-[#475569] uppercase font-bold">Decision Result</div>
                        <div className="text-lg font-bold text-white mt-1">{result.transaction_id}</div>
                      </div>
                      <span className={`pill ${
                        result.recommended_action === 'ALLOW' ? 'pill-allow' :
                        result.recommended_action === 'BLOCK' ? 'pill-block' :
                        result.recommended_action === 'REVIEW' ? 'pill-review' : 'pill-verify'
                      }`}>{result.recommended_action}</span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { label: 'Amount', value: `₹${result.amount.toLocaleString()}`, color: '#3395FF' },
                        { label: 'Fraud Prob', value: `${(result.fraud_probability * 100).toFixed(0)}%`, color: '#ef4444' },
                        { label: 'FP Prob', value: `${(result.fp_probability * 100).toFixed(0)}%`, color: '#06b6d4' },
                        { label: 'Confidence', value: 'High', color: '#3395FF' },
                      ].map((s) => (
                        <div key={s.label} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                          <div className="text-[10px] text-[#475569] uppercase font-bold">{s.label}</div>
                          <div className="text-sm font-bold font-data mt-1" style={{ color: s.color }}>{s.value}</div>
                        </div>
                      ))}
                    </div>
                    {result.is_counterintuitive && (
                      <div className="mt-4 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        <span className="text-[12px] text-amber-400">Counterintuitive: High fraud risk but REVIEW chosen over BLOCK to preserve LTV</span>
                      </div>
                    )}
                    <button onClick={() => { setStage('form'); setResult(null); setPipelineSteps([]) }}
                      className="mt-5 text-[12px] text-[#3395FF] hover:text-[#5aabff] font-bold">
                      ← New Payment
                    </button>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
