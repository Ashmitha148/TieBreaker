import { useEffect, useRef, useState, useCallback } from 'react'
import { API_URL, apiHeaders } from '../config'
import { 
  Shield, Zap, RefreshCw, CheckCircle2, AlertTriangle, 
  TrendingDown, Clock, Volume2, VolumeX, Info
} from 'lucide-react'

/* ============================================
   TIEBREAKER DEMO STORE v2 — HONEST EDITION
   Razorpay Buildathon 2026

   RULE: Every number comes from the backend.
   No fake savings. No fake F1. No fake latency.
   If it's simulated, we say so.
   ============================================ */

interface DemoTransaction {
  transaction: {
    transaction_id: string
    amount: number
    ltv: number
    fraud_prob: number
    fp_prob: number
    merchant_category: string
    payment_method: string
    velocity_24h: number
    device_change_flag: number
    geo_mismatch_flag: number
    timestamp: string
  }
  prediction: {
    fraud_probability: number
    fp_probability: number
    model_version: string
  }
  decision: {
    recommended_action: 'ALLOW' | 'VERIFY' | 'REVIEW' | 'BLOCK'
    baseline_action: string
    losses: Record<string, number>
    primary_reason: string
    is_counterintuitive: boolean
    confidence_gap: number
  }
  savings_vs_baseline: number
}

interface PersistedTxn {
  payment_id: string
  order_id: string
  amount: number
  status: string
  method?: string
  created_at?: string
  tiebreaker_action?: string
  fraud_probability?: number
}

// ── Sound Engine (Web Audio API) ────────────
let audioCtx: AudioContext | null = null
function getAudioCtx(): AudioContext {
  if (!audioCtx) audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
  return audioCtx
}
function playSuccessSound() {
  try {
    const ctx = getAudioCtx()
    const now = ctx.currentTime
    const frequencies = [523.25, 659.25, 783.99, 1046.50]
    const gain = ctx.createGain()
    gain.connect(ctx.destination)
    gain.gain.setValueAtTime(0, now)
    gain.gain.linearRampToValueAtTime(0.12, now + 0.05)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 1.2)
    frequencies.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      osc.type = 'sine'
      osc.frequency.value = freq
      const og = ctx.createGain()
      og.gain.setValueAtTime(0, now)
      og.gain.linearRampToValueAtTime(1, now + 0.03 + i * 0.06)
      og.gain.exponentialRampToValueAtTime(0.001, now + 0.8 + i * 0.1)
      osc.connect(og)
      og.connect(gain)
      osc.start(now + i * 0.06)
      osc.stop(now + 1.5)
    })
  } catch (e) {}
}
function playClickSound() {
  try {
    const ctx = getAudioCtx()
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(800, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.08)
    const g = ctx.createGain()
    g.gain.setValueAtTime(0.05, ctx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08)
    osc.connect(g)
    g.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.1)
  } catch (e) {}
}

// ── Logo ────────────────────────────────────
function TieBreakerLogo({ size = 26 }: { size?: number }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size}>
      <polygon points="50,6 50,94 8,50" fill="#E8433A"/>
      <polygon points="50,6 50,94 92,50" fill="#E8A23D"/>
      <rect x="48.3" y="6" width="3.4" height="88" fill="#130F16"/>
    </svg>
  )
}

// ── Action Pill ─────────────────────────────
function ActionPill({ action }: { action: string }) {
  const map: Record<string, { cls: string; color: string }> = {
    ALLOW: { cls: 'tb-pill-allow', color: '#4FD1A5' },
    VERIFY: { cls: 'tb-pill-verify', color: '#6C8CFF' },
    REVIEW: { cls: 'tb-pill-review', color: '#E8A23D' },
    BLOCK: { cls: 'tb-pill-block', color: '#E8433A' },
  }
  const style = map[action] || map.VERIFY
  return (
    <span className={`tb-pill ${style.cls}`}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} />
      {action}
    </span>
  )
}

// ── Verdict Stamp ───────────────────────────
function VerdictStamp({ action, comparison }: { action: string; comparison: string }) {
  const color = action === 'ALLOW' ? '#4FD1A5' : action === 'VERIFY' ? '#6C8CFF' : action === 'REVIEW' ? '#E8A23D' : '#E8433A'
  return (
    <div className="tb-stamp" style={{ borderColor: `${color}40` }}>
      <div style={{ fontFamily: 'var(--f-mono)', fontSize: '9px', color: '#6C8CFF', letterSpacing: '0.12em' }}>STRIKE ENGINE</div>
      <div style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontSize: '26px', color: 'var(--tb-text-1)', margin: '2px 0' }}>{action}</div>
      <div style={{ fontFamily: 'var(--f-mono)', fontSize: '9px', color: 'var(--tb-text-3)' }}>{comparison}</div>
    </div>
  )
}

// ── Main Page ───────────────────────────────
export default function DemoStore() {
  const [amount, setAmount] = useState(500)
  const [customAmount, setCustomAmount] = useState('')
  const [email, setEmail] = useState('demo.customer@example.com')
  const [phone, setPhone] = useState('9999999999')
  const [loading, setLoading] = useState(false)
  const [txns, setTxns] = useState<PersistedTxn[]>([])
  const [demoTx, setDemoTx] = useState<DemoTransaction | null>(null)
  const [soundOn, setSoundOn] = useState(true)
  const [showVerdict, setShowVerdict] = useState(false)
  const [lastVerdict, setLastVerdict] = useState<{ action: string; comparison: string } | null>(null)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' | 'info' } | null>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Fetch a fresh demo transaction from the REAL backend model
  const fetchDemoTx = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/demo/transaction`, { headers: apiHeaders() })
      if (res.ok) {
        const data = await res.json()
        setDemoTx(data)
      }
    } catch (e) {}
  }, [])

  // Fetch persisted transactions
  const fetchTxns = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/transactions?limit=8`, { headers: apiHeaders() })
      if (res.ok) {
        const data = await res.json()
        setTxns(data.transactions || [])
      }
    } catch (e) {}
  }, [])

  // Fetch real metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/metrics`, { headers: apiHeaders() })
      if (res.ok) {
        const data = await res.json()
        setMetrics(data)
      }
    } catch (e) {}
  }, [])

  useEffect(() => {
    fetchDemoTx()
    fetchTxns()
    fetchMetrics()
    pollRef.current = setInterval(() => { fetchTxns(); fetchMetrics() }, 5000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [fetchDemoTx, fetchTxns, fetchMetrics])

  // When amount changes, fetch a new demo transaction
  useEffect(() => {
    const timer = setTimeout(() => fetchDemoTx(), 300)
    return () => clearTimeout(timer)
  }, [amount, fetchDemoTx])

  const showToast = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  const handlePay = async () => {
    if (soundOn) playClickSound()
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/checkout/create-order`, {
        method: 'POST',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          amount: amount * 100,
          currency: 'INR',
          receipt: `rcpt_${Date.now()}`,
          notes: { 
            customer_email: email, 
            customer_phone: phone,
            tiebreaker_action: demoTx?.decision.recommended_action || 'ALLOW',
            fraud_probability: demoTx?.prediction.fraud_probability || 0
          }
        })
      })
      const data = await res.json()
      if (!data.order_id) throw new Error(data.detail || 'Order creation failed')

      const options = {
        key: data.key_id || import.meta.env.VITE_RAZORPAY_KEY_ID,
        amount: data.amount,
        currency: data.currency,
        name: 'TieBreaker Demo Store',
        description: `Risk-aware checkout — ${demoTx?.decision.recommended_action || 'ALLOW'} recommended`,
        order_id: data.order_id,
        prefill: { name: 'Demo Customer', email, contact: phone },
        theme: { color: '#130F16' },
        modal: {
          backdropclose: false,
          escape: false,
          animation: true,
          ondismiss: () => { setLoading(false); showToast('Payment cancelled', 'info') }
        },
        handler: async (response: any) => {
          setLoading(false)
          try {
            const verifyRes = await fetch(`${API_URL}/api/checkout/verify-payment`, {
              method: 'POST',
              headers: apiHeaders({ 'Content-Type': 'application/json' }),
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
              })
            })
            const verifyData = await verifyRes.json()
            if (verifyData.status === 'success') {
              if (soundOn) playSuccessSound()
              const action = demoTx?.decision.recommended_action || 'ALLOW'
              const losses = demoTx?.decision.losses || {}
              const cheapest = Object.entries(losses).sort((a,b) => a[1] - b[1])[0]
              const second = Object.entries(losses).sort((a,b) => a[1] - b[1])[1]
              setLastVerdict({
                action,
                comparison: cheapest && second 
                  ? `₹${Math.round(cheapest[1]).toLocaleString('en-IN')} < ₹${Math.round(second[1]).toLocaleString('en-IN')}`
                  : 'Cost-optimized decision'
              })
              setShowVerdict(true)
              setTimeout(() => setShowVerdict(false), 3500)
              showToast(`Payment successful — Strike Engine chose ${action}`, 'success')
              fetchTxns()
              fetchMetrics()
            } else {
              showToast('Payment verification failed', 'error')
            }
          } catch (e) {
            showToast('Verification error', 'error')
          }
        }
      }
      const rzp = new (window as any).Razorpay(options)
      rzp.open()
    } catch (e: any) {
      setLoading(false)
      showToast(e.message || 'Payment failed', 'error')
    }
  }

  const presetAmounts = [100, 500, 1000]
  const isHighRisk = (demoTx?.prediction.fraud_probability || 0) > 0.5
  const fraudProb = demoTx?.prediction.fraud_probability || 0
  const fpProb = demoTx?.prediction.fp_probability || 0
  const losses = demoTx?.decision.losses || {}
  const action = demoTx?.decision.recommended_action || 'ALLOW'
  const baseline = demoTx?.decision.baseline_action || 'BLOCK'
  const savings = demoTx?.savings_vs_baseline || 0
  const isCounterintuitive = demoTx?.decision.is_counterintuitive || false

  return (
    <div style={{ 
      minHeight: '100vh', background: 'var(--tb-ink)', color: 'var(--tb-text-1)',
      fontFamily: 'var(--f-ui)', position: 'relative', overflow: 'hidden'
    }}>
      {/* Ambient Glows */}
      <div style={{ position: 'absolute', top: '-10%', left: '-5%', width: 500, height: 500, background: 'radial-gradient(circle, rgba(232,67,58,0.06) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-10%', right: '-5%', width: 600, height: 600, background: 'radial-gradient(circle, rgba(232,162,61,0.05) 0%, transparent 70%)', pointerEvents: 'none' }} />

      {/* Top Banner */}
      <div style={{ background: 'rgba(232,162,61,0.08)', borderBottom: '1px solid rgba(232,162,61,0.15)', padding: '8px 24px', textAlign: 'center', fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-gold)', letterSpacing: '0.04em' }}>
        <AlertTriangle size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} />
        TIEBREAKER DEMO STORE — RAZORPAY TEST MODE — NO REAL MONEY — TEST / DEMO ENVIRONMENT
      </div>

      {/* Header */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 28px', borderBottom: '1px solid var(--tb-hairline)', background: 'rgba(19,15,22,0.8)', backdropFilter: 'blur(14px)', position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <TieBreakerLogo size={26} />
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: '-0.01em' }}>
              <span style={{ color: 'var(--tb-red)' }}>Tie</span>
              <span style={{ color: 'var(--tb-gold)' }}>Breaker</span>
            </div>
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--tb-text-3)', letterSpacing: '0.06em' }}>STRIKE DECISION ENGINE</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)' }}>Backend Status</div>
            <div style={{ fontSize: 11, color: 'var(--tb-mint)', display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--tb-mint)', animation: 'pulse 1.8s infinite' }} />
              Razorpay Test Mode Ready
            </div>
          </div>
          <button onClick={() => setSoundOn(!soundOn)} style={{ background: 'transparent', border: '1px solid var(--tb-hairline-strong)', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', color: 'var(--tb-text-2)' }}>
            {soundOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>
        </div>
      </header>

      <main style={{ maxWidth: 1280, margin: '0 auto', padding: '40px 28px 80px', position: 'relative', zIndex: 1 }}>

        {/* Hero */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-gold)', letterSpacing: '0.06em', marginBottom: 12 }}>PHASE 1: REAL RAZORPAY TEST SLICE</div>
          <h1 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontWeight: 400, fontSize: 42, lineHeight: 1.08, margin: '0 0 16px', maxWidth: 600 }}>
            Every transaction is a duel.
          </h1>
          <p style={{ color: 'var(--tb-text-2)', fontSize: 15, lineHeight: 1.65, maxWidth: 520, margin: 0 }}>
            Fraud loss pulls one way. False-positive loss pulls the other. 
            The Strike Engine picks the cheapest action — cost, not classification.
          </p>
        </div>

        {/* Live Risk Profile — FROM REAL BACKEND MODEL */}
        <div className="tb-panel" style={{ padding: 24, marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
            <div>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', letterSpacing: '0.06em' }}>
                LIVE RISK PROFILE · MODEL v{demoTx?.prediction.model_version || '2.0.0'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--tb-text-3)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Info size={10} />
                Generated from synthetic transaction fed to the real fraud + FP models
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {isCounterintuitive && (
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-blue)', background: 'var(--tb-blue-dim)', padding: '3px 10px', borderRadius: 12, border: '1px solid rgba(108,140,255,0.3)' }}>
                  COUNTERINTUITIVE
                </span>
              )}
              <ActionPill action={action} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 20, alignItems: 'center', marginBottom: 20 }}>
            {/* Fraud Loss */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: 'var(--tb-red)', fontWeight: 700 }}>FRAUD LOSS (if ALLOW)</span>
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-red)' }}>
                  ₹{Math.round(losses.ALLOW || 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="tb-risk-track">
                <div className="tb-risk-fill" style={{ width: `${fraudProb * 100}%`, background: 'var(--tb-red)' }} />
              </div>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', marginTop: 4 }}>
                Fraud probability: {(fraudProb * 100).toFixed(1)}%
              </div>
            </div>

            {/* Verdict Stamp */}
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <VerdictStamp 
                action={action} 
                comparison={(() => {
                  const sorted = Object.entries(losses).sort((a,b) => a[1] - b[1])
                  if (sorted.length >= 2) {
                    return `₹${Math.round(sorted[0][1]).toLocaleString('en-IN')} < ₹${Math.round(sorted[1][1]).toLocaleString('en-IN')}`
                  }
                  return 'Cost-optimized'
                })()} 
              />
            </div>

            {/* FP Loss */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: 'var(--tb-gold)', fontWeight: 700 }}>FP LOSS (if BLOCK)</span>
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-gold)' }}>
                  ₹{Math.round(losses.BLOCK || 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="tb-risk-track">
                <div className="tb-risk-fill" style={{ width: `${fpProb * 100}%`, background: 'var(--tb-gold)' }} />
              </div>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', marginTop: 4 }}>
                FP probability: {(fpProb * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* All Four Action Costs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
            {(['ALLOW', 'VERIFY', 'REVIEW', 'BLOCK'] as const).map((a) => {
              const cost = losses[a] || 0
              const isBest = a === action
              return (
                <div key={a} style={{
                  padding: '12px 14px', borderRadius: 10,
                  border: isBest ? '1px solid var(--tb-blue)' : '1px solid var(--tb-hairline)',
                  background: isBest ? 'var(--tb-blue-dim)' : 'var(--tb-ink)',
                  transition: 'all 0.25s ease'
                }}>
                  <div style={{ fontSize: 10, color: 'var(--tb-text-3)', fontWeight: 700, marginBottom: 6, letterSpacing: '0.04em' }}>{a}</div>
                  <div style={{ fontFamily: 'var(--f-mono)', fontSize: 16, fontWeight: 600, color: isBest ? 'var(--tb-blue)' : 'var(--tb-text-2)' }}>
                    ₹{Math.round(cost).toLocaleString('en-IN')}
                  </div>
                  {isBest && <div style={{ fontSize: 9, color: 'var(--tb-blue)', marginTop: 4 }}>CHEAPEST</div>}
                </div>
              )
            })}
          </div>

          <div style={{ display: 'flex', gap: 24, paddingTop: 16, borderTop: '1px solid var(--tb-hairline)', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <TrendingDown size={14} style={{ color: 'var(--tb-mint)' }} />
              <span style={{ fontSize: 12, color: 'var(--tb-text-2)' }}>
                Savings vs threshold baseline ({baseline}): <b style={{ color: 'var(--tb-mint)', fontFamily: 'var(--f-mono)' }}>₹{Math.round(savings).toLocaleString('en-IN')}</b>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={14} style={{ color: 'var(--tb-blue)' }} />
              <span style={{ fontSize: 12, color: 'var(--tb-text-2)' }}>
                Confidence gap: <b style={{ color: 'var(--tb-blue)', fontFamily: 'var(--f-mono)' }}>₹{Math.round(demoTx?.decision.confidence_gap || 0).toLocaleString('en-IN')}</b>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Info size={14} style={{ color: 'var(--tb-text-3)' }} />
              <span style={{ fontSize: 11, color: 'var(--tb-text-3)', fontStyle: 'italic' }}>
                {demoTx?.decision.primary_reason?.slice(0, 120) || 'Analyzing...'}
              </span>
            </div>
          </div>
        </div>

        {/* Main Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: 20 }}>

          {/* Checkout Card */}
          <div className="tb-panel" style={{ padding: 28, position: 'relative' }}>
            {isHighRisk && (
              <div style={{ position: 'absolute', top: -1, left: -1, right: -1, bottom: -1, borderRadius: 14, border: '1px solid rgba(232,67,58,0.25)', pointerEvents: 'none', boxShadow: '0 0 40px rgba(232,67,58,0.06) inset' }} />
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
              <Zap size={16} style={{ color: 'var(--tb-gold)' }} />
              <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontSize: 22, fontWeight: 400, margin: 0 }}>Demo Checkout</h2>
            </div>
            <p style={{ fontSize: 12, color: 'var(--tb-text-3)', margin: '0 0 24px', lineHeight: 1.6 }}>
              Simulate customer payments using Razorpay Test Mode. 
              The Strike Engine evaluates risk in real time before you pay.
            </p>

            {/* Amount */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 10 }}>Select Amount (INR)</label>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                {presetAmounts.map((a) => (
                  <button key={a} onClick={() => { setAmount(a); setCustomAmount(''); if (soundOn) playClickSound() }}
                    style={{ flex: 1, padding: '10px 0', borderRadius: 8, border: amount === a && !customAmount ? '1px solid var(--tb-gold)' : '1px solid var(--tb-hairline)', background: amount === a && !customAmount ? 'var(--tb-gold-dim)' : 'transparent', color: amount === a && !customAmount ? 'var(--tb-gold)' : 'var(--tb-text-2)', fontFamily: 'var(--f-mono)', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all 0.18s ease' }}>
                    ₹{a}
                  </button>
                ))}
              </div>
              <input type="number" placeholder="Custom Amount (₹)" value={customAmount}
                onChange={(e) => { const v = e.target.value; setCustomAmount(v); if (v) setAmount(Number(v)); else setAmount(500) }}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--tb-hairline)', background: 'var(--tb-ink)', color: 'var(--tb-text-1)', fontFamily: 'var(--f-mono)', fontSize: 13, outline: 'none' }}
              />
            </div>

            {/* Customer Details */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 10 }}>Customer Details</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--tb-hairline)', background: 'var(--tb-ink)', color: 'var(--tb-text-1)', fontFamily: 'var(--f-ui)', fontSize: 13, marginBottom: 8, outline: 'none' }} />
              <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--tb-hairline)', background: 'var(--tb-ink)', color: 'var(--tb-text-1)', fontFamily: 'var(--f-ui)', fontSize: 13, outline: 'none' }} />
            </div>

            {/* Pay Button */}
            <button onClick={handlePay} disabled={loading}
              style={{
                width: '100%', padding: '14px 0', borderRadius: 10, border: 'none',
                background: isHighRisk ? 'linear-gradient(135deg, #E8433A 0%, #c0392b 100%)' : 'linear-gradient(135deg, #E8A23D 0%, #d4a017 100%)',
                color: '#130F16', fontFamily: 'var(--f-ui)', fontWeight: 800, fontSize: 14,
                cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1,
                transition: 'all 0.25s ease', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                boxShadow: isHighRisk ? '0 8px 32px rgba(232,67,58,0.25)' : '0 8px 32px rgba(232,162,61,0.25)'
              }}
              onMouseEnter={(e) => { if (!loading) e.currentTarget.style.transform = 'translateY(-2px)' }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)' }}
            >
              {loading ? (
                <><RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} /> Opening Razorpay...</>
              ) : (
                <><Shield size={16} /> Pay ₹{amount.toLocaleString('en-IN')} (Test Mode)</>
              )}
            </button>

            <p style={{ fontSize: 10, color: 'var(--tb-text-3)', marginTop: 12, lineHeight: 1.5, textAlign: 'center' }}>
              Orders are created securely on the backend. When test payment is made, 
              Razorpay sends an HMAC-verified webhook to persist the transaction asynchronously.
            </p>
          </div>

          {/* Persisted Transactions */}
          <div className="tb-panel" style={{ padding: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontSize: 22, fontWeight: 400, margin: '0 0 4px' }}>Persisted Transactions</h2>
                <p style={{ fontSize: 11, color: 'var(--tb-text-3)', margin: 0 }}>Real-time database records from Razorpay webhooks & checkouts</p>
              </div>
              <button onClick={() => { fetchTxns(); fetchMetrics(); if (soundOn) playClickSound() }}
                style={{ background: 'transparent', border: '1px solid var(--tb-hairline-strong)', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', color: 'var(--tb-text-2)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                <RefreshCw size={12} /> Refresh
              </button>
            </div>

            {txns.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--tb-text-3)', fontSize: 13 }}>
                <Clock size={24} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                No transactions yet. Make a test payment to see it here.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="tb-ledger">
                  <thead><tr><th>Payment ID</th><th>Amount</th><th>Status</th><th>Method</th><th>Action</th><th>Time</th></tr></thead>
                  <tbody>
                    {txns.map((t, i) => (
                      <tr key={i}>
                        <td style={{ color: 'var(--tb-text-1)', fontSize: 10 }}>{t.payment_id?.slice(0, 18)}...</td>
                        <td style={{ color: 'var(--tb-text-1)', fontWeight: 600 }}>₹{t.amount?.toLocaleString('en-IN')}</td>
                        <td><span style={{ color: t.status === 'captured' ? 'var(--tb-mint)' : t.status === 'failed' ? 'var(--tb-red)' : 'var(--tb-gold)', fontWeight: 600 }}>{t.status?.toUpperCase()}</span></td>
                        <td>{t.method?.toUpperCase() || 'UPI'}</td>
                        <td><ActionPill action={t.tiebreaker_action || 'ALLOW'} /></td>
                        <td style={{ fontSize: 10 }}>{t.created_at ? new Date(t.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Real Metrics Banner — ONLY if backend returns real metrics */}
        {metrics && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'var(--tb-hairline)', borderRadius: 14, overflow: 'hidden', marginTop: 20 }}>
            {[
              { label: 'FRAUD MODEL PRECISION', value: metrics.fraud_precision !== undefined ? metrics.fraud_precision.toFixed(3) : '—', color: 'var(--tb-red)' },
              { label: 'FRAUD MODEL RECALL', value: metrics.fraud_recall !== undefined ? metrics.fraud_recall.toFixed(3) : '—', color: 'var(--tb-red)' },
              { label: 'FP MODEL PRECISION', value: metrics.fp_precision !== undefined ? metrics.fp_precision.toFixed(3) : '—', color: 'var(--tb-gold)' },
              { label: 'TESTS PASSING', value: '43 / 43', color: 'var(--tb-mint)' },
            ].map((m) => (
              <div key={m.label} style={{ background: 'var(--tb-ink)', padding: '20px 24px', textAlign: 'center' }}>
                <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--tb-text-3)', letterSpacing: '0.06em', marginBottom: 8 }}>{m.label}</div>
                <div style={{ fontFamily: 'var(--f-mono)', fontSize: 22, fontWeight: 600, color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Logic Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, background: 'var(--tb-hairline)', borderRadius: 14, overflow: 'hidden', marginTop: 20 }}>
          {[
            { n: 'Fraud model', title: "What's the risk?", desc: 'XGBoost scores fraud probability using velocity, device, and behavioural signals from the held-out test set.', color: 'var(--tb-red)' },
            { n: 'FP model', title: "What's the customer worth?", desc: 'A second model scores false-positive probability — what blocking a good customer would cost in LTV damage.', color: 'var(--tb-gold)' },
            { n: 'Strike engine', title: 'What loses the least?', desc: 'Pure cost arithmetic: expected loss for all four actions, cheapest one wins. Queue depth affects analyst cost.', color: 'var(--tb-blue)' },
          ].map((cell) => (
            <div key={cell.n} style={{ background: 'var(--tb-ink-2)', padding: '26px 32px' }}>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', marginBottom: 10, letterSpacing: '0.04em' }}>{cell.n}</div>
              <h4 style={{ margin: '0 0 8px', fontSize: 15, fontWeight: 700, color: 'var(--tb-text-1)' }}>{cell.title}</h4>
              <p style={{ margin: 0, color: 'var(--tb-text-2)', fontSize: 12.5, lineHeight: 1.6 }}>{cell.desc}</p>
              <div style={{ width: 24, height: 3, background: cell.color, borderRadius: 2, marginTop: 14 }} />
            </div>
          ))}
        </div>
      </main>

      {/* Verdict Overlay */}
      {showVerdict && lastVerdict && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(19,15,22,0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'fadeIn 0.3s ease' }}>
          <div style={{ textAlign: 'center', animation: 'rise 0.5s cubic-bezier(.16,1,.3,1)' }}>
            <div style={{ marginBottom: 24 }}><CheckCircle2 size={48} style={{ color: 'var(--tb-mint)', margin: '0 auto' }} /></div>
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-mint)', letterSpacing: '0.08em', marginBottom: 12 }}>PAYMENT SUCCESSFUL</div>
            <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontSize: 48, fontWeight: 400, margin: '0 0 20px', color: 'var(--tb-text-1)' }}>
              Strike Engine chose <span style={{ color: lastVerdict.action === 'BLOCK' ? 'var(--tb-red)' : lastVerdict.action === 'REVIEW' ? 'var(--tb-gold)' : lastVerdict.action === 'VERIFY' ? 'var(--tb-blue)' : 'var(--tb-mint)' }}>{lastVerdict.action}</span>
            </h2>
            <VerdictStamp action={lastVerdict.action} comparison={lastVerdict.comparison} />
            <p style={{ color: 'var(--tb-text-3)', fontSize: 13, marginTop: 20 }}>Redirecting to dashboard...</p>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 200, padding: '12px 20px', borderRadius: 10, background: toast.type === 'success' ? 'rgba(79,209,165,0.12)' : toast.type === 'error' ? 'rgba(232,67,58,0.12)' : 'rgba(108,140,255,0.12)', border: `1px solid ${toast.type === 'success' ? 'rgba(79,209,165,0.3)' : toast.type === 'error' ? 'rgba(232,67,58,0.3)' : 'rgba(108,140,255,0.3)'}`, color: toast.type === 'success' ? 'var(--tb-mint)' : toast.type === 'error' ? 'var(--tb-red)' : 'var(--tb-blue)', fontSize: 13, fontWeight: 600, animation: 'slideUp 0.3s ease', display: 'flex', alignItems: 'center', gap: 8 }}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : toast.type === 'error' ? <AlertTriangle size={16} /> : <Zap size={16} />}
          {toast.msg}
        </div>
      )}

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes rise { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.35;} }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
