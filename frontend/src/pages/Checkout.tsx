import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CreditCard, Smartphone, Banknote, ArrowRight, Shield,
  Zap, CheckCircle, AlertTriangle, Clock, Brain, XCircle, Loader2
} from 'lucide-react'
import TransactionPipeline from '../components/TransactionPipeline'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { API_URL } from '../config'

// Razorpay SDK is loaded via <script> in index.html
declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => RazorpayInstance
  }
}

interface RazorpayOptions {
  key: string
  amount: number
  currency: string
  name: string
  description?: string
  order_id: string
  prefill?: { name?: string; email?: string; contact?: string }
  theme?: { color?: string }
  handler: (response: RazorpaySuccessResponse) => void
  modal?: { ondismiss?: () => void }
}

interface RazorpaySuccessResponse {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

interface RazorpayInstance {
  open(): void
  on(event: string, callback: (response: any) => void): void
}

interface VerifiedPayment {
  status: string
  transaction_id: string
  amount: number
  recommended_action: string
  fraud_probability: number
  fp_probability: number
  is_counterintuitive: boolean
}

export default function Checkout() {
  const [amount, setAmount] = useState('500')
  const [email, setEmail] = useState('user@example.com')
  const [phone, setPhone] = useState('9999999999')
  const [method, setMethod] = useState<'upi' | 'card' | 'netbanking'>('upi')
  const [stage, setStage] = useState<'form' | 'processing' | 'result' | 'error'>('form')
  const [result, setResult] = useState<VerifiedPayment | null>(null)
  const [pipelineSteps, setPipelineSteps] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const startPipeline = (data: VerifiedPayment) => {
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

    const fraudPct = (data.fraud_probability * 100).toFixed(0)
    const fpPct = (data.fp_probability * 100).toFixed(0)

    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 0 ? { ...step, status: 'completed', detail: '₹' + data.amount, timestamp: '14:23:01.000' } : step)), 400)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 1 ? { ...step, status: 'completed', detail: '12 txns/hr', timestamp: '14:23:01.120' } : step)), 900)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 2 ? { ...step, status: 'completed', detail: 'prob: ' + fraudPct + '%', timestamp: '14:23:01.280' } : step)), 1400)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 3 ? { ...step, status: 'completed', detail: 'prob: ' + fpPct + '%', timestamp: '14:23:01.310' } : step)), 1800)
    setTimeout(() => {
      setPipelineSteps(s => s.map((step, i) => i === 4 ? { ...step, status: 'active', detail: data.recommended_action, timestamp: '14:23:01.340' } : step))
      setResult(data)
    }, 2200)
    setTimeout(() => setPipelineSteps(s => s.map((step, i) => i === 5 ? { ...step, status: 'completed', detail: 'Done', timestamp: '14:23:01.400' } : step)), 2800)
    setTimeout(() => setStage('result'), 3200)
  }

  const handlePay = async () => {
    setErrorMsg(null)
    setLoading(true)

    // 1. Create order on backend
    let orderData: { order_id: string; amount: number; currency: string; key_id: string }
    try {
      const res = await fetch(`${API_URL}/api/payment/create-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: Number(amount) * 100, currency: 'INR' }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Backend error ${res.status}`)
      }
      orderData = await res.json()
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create order. Is the backend running with Razorpay keys configured?')
      setStage('error')
      setLoading(false)
      return
    }

    // 2. Open Razorpay checkout modal
    if (!window.Razorpay) {
      setErrorMsg('Razorpay SDK not loaded. Check your internet connection.')
      setStage('error')
      setLoading(false)
      return
    }

    const options: RazorpayOptions = {
      key: orderData.key_id,
      amount: orderData.amount,
      currency: orderData.currency,
      name: 'TieBreaker',
      description: 'Payment — ₹' + amount,
      order_id: orderData.order_id,
      prefill: {
        name: 'Test User',
        email: email,
        contact: phone,
      },
      theme: {
        color: '#3395FF',
      },
      handler: async (response: RazorpaySuccessResponse) => {
        // 3. Verify payment on backend (runs fraud pipeline too)
        setLoading(true)
        try {
          const verifyRes = await fetch(`${API_URL}/api/payment/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          })
          if (!verifyRes.ok) {
            const err = await verifyRes.json().catch(() => ({}))
            throw new Error(err.detail || `Verification failed (${verifyRes.status})`)
          }
          const verified: VerifiedPayment = await verifyRes.json()
          setLoading(false)
          startPipeline(verified)
        } catch (err: any) {
          setErrorMsg(err.message || 'Payment verification failed')
          setStage('error')
          setLoading(false)
        }
      },
      modal: {
        ondismiss: () => {
          setLoading(false)
        },
      },
    }

    const rzp = new window.Razorpay(options)

    rzp.on('payment.failed', (response: any) => {
      setErrorMsg(response.error?.description || 'Payment failed. Please try again.')
      setStage('error')
      setLoading(false)
    })

    rzp.open()
    setLoading(false)
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
                    <button onClick={handlePay} disabled={loading}
                      className="w-full py-3 bg-gradient-to-r from-[#3395FF] to-[#2563eb] text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-[#3395FF]/25 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed">
                      {loading ? (
                        <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</>
                      ) : (
                        <>Pay ₹{Number(amount).toLocaleString('en-IN')}<ArrowRight className="w-4 h-4" /></>
                      )}
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

            {stage === 'error' && errorMsg && (
              <motion.div key="error" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="float-card p-6 border-red-500/30">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
                      <XCircle className="w-5 h-5 text-red-400" />
                    </div>
                    <div>
                      <div className="text-[10px] text-red-400 uppercase font-bold">Payment Failed</div>
                      <div className="text-sm font-bold text-white mt-0.5">Transaction could not be completed</div>
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-red-500/5 border border-red-500/15">
                    <p className="text-[12px] text-red-300">{errorMsg}</p>
                  </div>
                  <button onClick={() => { setStage('form'); setErrorMsg(null); setPipelineSteps([]) }}
                    className="mt-4 text-[12px] text-[#3395FF] hover:text-[#5aabff] font-bold">
                    ← Try Again
                  </button>
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
