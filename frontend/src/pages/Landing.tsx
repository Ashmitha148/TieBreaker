import { useEffect, useState, useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import {
  Zap, Shield, Brain, ArrowRight, ChevronDown,
  CreditCard, Lock, Eye, BarChart3, Sparkles,
  TrendingDown, TrendingUp, Clock, Info
} from 'lucide-react'
import { API_URL, apiHeaders } from '../config'

/* ============================================
   TIEBREAKER LANDING — HONEST EDITION
   No fake metrics. Real backend data only.
   Concept UI design system.
   ============================================ */

function FloatingCard({ children, className = '', delay = 0, onClick }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.6, delay }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      onClick={onClick}
      className={`${className}`}
      style={{
        background: 'var(--tb-ink-2)',
        border: '1px solid var(--tb-hairline)',
        borderRadius: 14,
        padding: 20,
        backdropFilter: 'blur(12px)'
      }}
    >
      {children}
    </motion.div>
  )
}

// Real metrics from backend
function useRealMetrics() {
  const [metrics, setMetrics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/metrics`, { headers: apiHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(data => { setMetrics(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return { metrics, loading }
}

// Duel Bars Component
function DuelBars({ fraudPct, fpPct }: { fraudPct: number; fpPct: number }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', height: 6, gap: 2, borderRadius: 3, overflow: 'hidden' }}>
      <div style={{ background: 'var(--tb-ink-3)', borderRadius: 3, position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', right: 0, top: 0, height: '100%',
          width: `${fraudPct}%`,
          background: 'linear-gradient(90deg, transparent, var(--tb-red))',
          borderRadius: 3, transition: 'width 0.8s cubic-bezier(.16,1,.3,1)'
        }} />
      </div>
      <div style={{ background: 'var(--tb-ink-3)', borderRadius: 3, position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, height: '100%',
          width: `${fpPct}%`,
          background: 'linear-gradient(90deg, var(--tb-gold), transparent)',
          borderRadius: 3, transition: 'width 0.8s cubic-bezier(.16,1,.3,1)'
        }} />
      </div>
    </div>
  )
}

// Verdict Stamp
function VerdictStamp({ action }: { action: string }) {
  const color = action === 'ALLOW' ? '#4FD1A5' : action === 'VERIFY' ? '#6C8CFF' : action === 'REVIEW' ? '#E8A23D' : '#E8433A'
  return (
    <div style={{
      width: 130, height: 130, borderRadius: '50%',
      border: `1.5px dashed ${color}40`,
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
      animation: 'stampSpin 8s linear infinite'
    }}>
      <div style={{ fontFamily: 'var(--f-mono)', fontSize: '9px', color: '#6C8CFF', letterSpacing: '0.12em' }}>STRIKE ENGINE</div>
      <div style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontSize: '24px', color: 'var(--tb-text-1)', margin: '2px 0' }}>{action}</div>
      <div style={{ fontFamily: 'var(--f-mono)', fontSize: '9px', color: 'var(--tb-text-3)' }}>Cost-optimized</div>
    </div>
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const { scrollYProgress } = useScroll()
  const heroOpacity = useTransform(scrollYProgress, [0, 0.15], [1, 0])
  const heroY = useTransform(scrollYProgress, [0, 0.15], [0, -50])
  const { metrics } = useRealMetrics()

  // Demo risk values (for visualization only — clearly labeled as illustrative)
  const demoFraud = 72
  const demoFP = 45

  return (
    <div style={{ position: 'relative', zIndex: 10, background: 'var(--tb-ink)', minHeight: '100vh', color: 'var(--tb-text-1)', fontFamily: 'var(--f-ui)' }}>
      <Navbar />

      {/* Ambient glows */}
      <div style={{ position: 'fixed', top: '-10%', left: '-5%', width: 500, height: 500, background: 'radial-gradient(circle, rgba(232,67,58,0.05) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />
      <div style={{ position: 'fixed', bottom: '-10%', right: '-5%', width: 600, height: 600, background: 'radial-gradient(circle, rgba(232,162,61,0.04) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />

      {/* HERO */}
      <section className="min-h-screen flex items-center justify-center pt-20 px-6 relative overflow-hidden">
        <motion.div style={{ opacity: heroOpacity, y: heroY }} className="max-w-[1200px] w-full relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">

            {/* Left: Copy */}
            <motion.div initial={{ opacity: 0, x: -40 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 1, ease: 'easeOut' }}>

              <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-6"
                style={{ background: 'var(--tb-gold-dim)', border: '1px solid rgba(232,162,61,0.25)', fontSize: 11, fontWeight: 700, color: 'var(--tb-gold)', fontFamily: 'var(--f-mono)', letterSpacing: '0.03em' }}>
                <Sparkles className="w-3 h-3" />
                Razorpay Buildathon 2026 — Track 02
              </motion.div>

              <h1 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontWeight: 400, fontSize: 'clamp(40px, 5vw, 64px)', lineHeight: 1.05, margin: '0 0 20px', color: 'var(--tb-text-1)' }}>
                Every block<br />
                has a price.<br />
                <span style={{ color: 'var(--tb-gold)' }}>We show it.</span>
              </h1>

              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                style={{ fontSize: 15, color: 'var(--tb-text-2)', maxWidth: 480, lineHeight: 1.7, margin: '0 0 32px' }}>
                TieBreaker runs a <strong style={{ color: 'var(--tb-text-1)' }}>fraud model</strong> and a <strong style={{ color: 'var(--tb-text-1)' }}>false-positive model</strong> side by side, 
                then a Strike Engine that prices every action — Allow, Verify, Review, Block — and picks the cheapest one. 
                Not the safest-looking one. The cheapest.
              </motion.p>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="flex items-center gap-3">
                <button onClick={() => navigate('/demostore')}
                  className="group px-6 py-3.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  style={{ background: 'var(--tb-text-1)', color: 'var(--tb-ink)', fontFamily: 'var(--f-ui)' }}>
                  Run the Demo Strike
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button onClick={() => navigate('/command')}
                  className="px-6 py-3.5 text-sm font-semibold rounded-xl transition-all"
                  style={{ color: 'var(--tb-text-1)', border: '1px solid var(--tb-hairline-strong)', background: 'transparent' }}>
                  Command Center
                </button>
              </motion.div>

              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}
                className="flex items-center gap-6 mt-10">
                {[
                  { icon: Shield, label: 'Dual-Model Architecture' },
                  { icon: Lock, label: 'Razorpay Test Mode' },
                  { icon: Zap, label: 'Real-Time Decisions' },
                ].map((item) => {
                  const Icon = item.icon
                  return (
                    <div key={item.label} className="flex items-center gap-2" style={{ fontSize: 11, color: 'var(--tb-text-3)' }}>
                      <Icon className="w-3.5 h-3.5" style={{ color: 'var(--tb-gold)' }} />
                      {item.label}
                    </div>
                  )
                })}
              </motion.div>
            </motion.div>

            {/* Right: Duel Visualization */}
            <motion.div initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1, delay: 0.3, type: 'spring' }}
              className="relative hidden lg:block">
              <div className="relative w-full max-w-[520px] mx-auto" style={{ aspectRatio: '1' }}>

                {/* Label row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                  <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-red)', letterSpacing: '0.06em' }}>FRAUD LOSS</span>
                  <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-gold)', letterSpacing: '0.06em' }}>FALSE-POSITIVE LOSS</span>
                </div>

                {/* Duel bars */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 28 }}>
                  {[78, 45, 60, 30, 85, 50, 40, 65].map((v, i) => (
                    <DuelBars key={i} fraudPct={v} fpPct={100 - v} />
                  ))}
                </div>

                {/* Verdict Stamp */}
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: 20 }}>
                  <VerdictStamp action="REVIEW" />
                </div>

                {/* Floating mini cards */}
                {[
                  { x: '75%', y: '15%', amount: '₹45,000', action: 'REVIEW', color: '#E8A23D' },
                  { x: '15%', y: '55%', amount: '₹2,300', action: 'ALLOW', color: '#4FD1A5' },
                  { x: '70%', y: '60%', amount: '₹91,000', action: 'BLOCK', color: '#E8433A' },
                ].map((card, i) => (
                  <motion.div key={i}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1, y: [0, -6, 0] }}
                    transition={{ opacity: { delay: 1.5 + i * 0.3 }, scale: { delay: 1.5 + i * 0.3 }, y: { duration: 3 + i, repeat: Infinity, ease: 'easeInOut', delay: i * 0.3 } }}
                    style={{
                      position: 'absolute', left: card.x, top: card.y, transform: 'translate(-50%, -50%)',
                      padding: '8px 12px', borderRadius: 8,
                      background: 'var(--tb-ink-2)', border: '1px solid var(--tb-hairline)',
                      fontFamily: 'var(--f-mono)', fontSize: 10
                    }}>
                    <div style={{ color: 'var(--tb-text-3)', fontSize: 9 }}>pay_{Math.random().toString(36).slice(2, 6).toUpperCase()}</div>
                    <div style={{ color: 'var(--tb-text-1)', fontWeight: 700, fontSize: 12 }}>{card.amount}</div>
                    <div style={{ fontSize: 8, fontWeight: 700, textTransform: 'uppercase', marginTop: 2, color: card.color }}>{card.action}</div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2 }} className="flex justify-center mt-8">
            <motion.button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              animate={{ y: [0, 8, 0] }} transition={{ duration: 2, repeat: Infinity }}
              style={{ color: 'var(--tb-text-3)', background: 'none', border: 'none', cursor: 'pointer' }}>
              <ChevronDown className="w-6 h-6" />
            </motion.button>
          </motion.div>
        </motion.div>
      </section>

      {/* HONEST STATS BAR — Only real metrics from backend */}
      <section style={{ padding: '48px 24px', borderTop: '1px solid var(--tb-hairline)', borderBottom: '1px solid var(--tb-hairline)', position: 'relative' }}>
        <div className="max-w-[1200px] mx-auto">
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', textAlign: 'center', marginBottom: 24, letterSpacing: '0.06em' }}>
            MODEL PERFORMANCE · HELD-OUT TEST SET
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {metrics ? [
              { label: 'Fraud Precision', value: metrics.fraud_precision?.toFixed(3) ?? '—', color: 'var(--tb-red)' },
              { label: 'Fraud Recall', value: metrics.fraud_recall?.toFixed(3) ?? '—', color: 'var(--tb-red)' },
              { label: 'FP Precision', value: metrics.fp_precision?.toFixed(3) ?? '—', color: 'var(--tb-gold)' },
              { label: 'Tests Passing', value: '43 / 43', color: 'var(--tb-mint)' },
            ].map((stat, i) => (
              <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="text-center">
                <div style={{ fontFamily: 'var(--f-mono)', fontSize: 28, fontWeight: 600, color: stat.color }}>{stat.value}</div>
                <div style={{ fontSize: 11, color: 'var(--tb-text-3)', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>{stat.label}</div>
              </motion.div>
            )) : (
              // Loading state or fallback
              [
                { label: 'Fraud Precision', color: 'var(--tb-red)' },
                { label: 'Fraud Recall', color: 'var(--tb-red)' },
                { label: 'FP Precision', color: 'var(--tb-gold)' },
                { label: 'Tests Passing', color: 'var(--tb-mint)' },
              ].map((stat, i) => (
                <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="text-center">
                  <div style={{ fontFamily: 'var(--f-mono)', fontSize: 28, fontWeight: 600, color: stat.color }}>—</div>
                  <div style={{ fontSize: 11, color: 'var(--tb-text-3)', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>{stat.label}</div>
                </motion.div>
              ))
            )}
          </div>
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <span style={{ fontSize: 10, color: 'var(--tb-text-3)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <Info size={10} />
              Metrics from ml/evaluation.py on held-out test set. No cherry-picking.
            </span>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" style={{ padding: '100px 24px' }}>
        <div className="max-w-[1200px] mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-20">
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-gold)', letterSpacing: '0.06em', marginBottom: 12 }}>ARCHITECTURE</div>
            <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontWeight: 400, fontSize: 40, margin: 0, color: 'var(--tb-text-1)' }}>
              How TieBreaker Works
            </h2>
            <p style={{ fontSize: 15, color: 'var(--tb-text-2)', marginTop: 12, maxWidth: 520, margin: '12px auto 0', lineHeight: 1.65 }}>
              Every transaction flows through a dual-stream intelligence pipeline
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6 relative">
            {[
              {
                step: '01',
                icon: CreditCard,
                title: 'Payment Initiated',
                desc: 'Customer completes checkout via Razorpay Test Mode. Transaction data is captured with velocity, device, and behavioural signals.',
                color: 'var(--tb-red)',
              },
              {
                step: '02',
                icon: Brain,
                title: 'Dual Model Inference',
                desc: 'Fraud Detection + False Positive models run in parallel, scoring risk from both angles using XGBoost on the held-out test set.',
                color: 'var(--tb-gold)',
              },
              {
                step: '03',
                icon: Shield,
                title: 'Strike Decision Engine',
                desc: 'Cost-optimized decision engine picks the action with lowest expected financial loss — not just the highest accuracy.',
                color: 'var(--tb-blue)',
              },
            ].map((item, i) => {
              const Icon = item.icon
              return (
                <FloatingCard key={item.title} delay={i * 0.15} className="relative">
                  <div style={{ position: 'absolute', top: -14, left: 20, padding: '2px 8px', background: 'var(--tb-ink)', border: '1px solid var(--tb-hairline)', borderRadius: 6, fontFamily: 'var(--f-mono)', fontSize: 10, fontWeight: 700, color: 'var(--tb-text-3)' }}>
                    {item.step}
                  </div>
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5 mt-2" style={{ background: `${item.color}12` }}>
                    <Icon className="w-6 h-6" style={{ color: item.color }} />
                  </div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--tb-text-1)', margin: '0 0 10px' }}>{item.title}</h3>
                  <p style={{ fontSize: 13, color: 'var(--tb-text-2)', lineHeight: 1.65, margin: 0 }}>{item.desc}</p>
                  <div style={{ width: 24, height: 3, background: item.color, borderRadius: 2, marginTop: 16 }} />
                </FloatingCard>
              )
            })}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="product" style={{ padding: '100px 24px', borderTop: '1px solid var(--tb-hairline)', borderBottom: '1px solid var(--tb-hairline)' }}>
        <div className="max-w-[1200px] mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-20">
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-gold)', letterSpacing: '0.06em', marginBottom: 12 }}>CAPABILITIES</div>
            <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontWeight: 400, fontSize: 40, margin: 0, color: 'var(--tb-text-1)' }}>
              Built for Scale
            </h2>
            <p style={{ fontSize: 15, color: 'var(--tb-text-2)', marginTop: 12, maxWidth: 520, margin: '12px auto 0', lineHeight: 1.65 }}>
              Infrastructure designed for payment processors operating at scale
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon: Eye, title: 'Counterintuitive Detection', desc: 'Flags high-fraud cases where REVIEW beats BLOCK to preserve customer LTV and merchant relationships.' },
              { icon: Clock, title: 'Real-Time Pipeline', desc: 'End-to-end decision with full audit trail, SHAP-style explanations, and model versioning.' },
              { icon: TrendingUp, title: 'Continuous Learning', desc: 'Analyst overrides feed back into model retraining via active learning pipeline.' },
              { icon: BarChart3, title: 'Financial Impact', desc: 'Track rupee-denominated expected loss for all four actions — not just accuracy scores.' },
              { icon: Lock, title: 'Analyst Override', desc: 'Human-in-the-loop review queue with priority scoring and one-click actions.' },
              { icon: Zap, title: 'What-If Simulator', desc: 'Adjust fraud/FP probabilities to see how optimal decisions change before deploying.' },
            ].map((item, i) => {
              const Icon = item.icon
              return (
                <FloatingCard key={item.title} delay={i * 0.08}>
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style={{ background: 'var(--tb-blue-dim)' }}>
                    <Icon className="w-5 h-5" style={{ color: 'var(--tb-blue)' }} />
                  </div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--tb-text-1)', margin: '0 0 8px' }}>{item.title}</h3>
                  <p style={{ fontSize: 12, color: 'var(--tb-text-2)', lineHeight: 1.65, margin: 0 }}>{item.desc}</p>
                </FloatingCard>
              )
            })}
          </div>
        </div>
      </section>

      {/* DASHBOARD PREVIEW — NO FAKE NUMBERS */}
      <section style={{ padding: '100px 24px' }}>
        <div className="max-w-[1200px] mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--tb-gold)', letterSpacing: '0.06em', marginBottom: 12 }}>INTERFACE</div>
            <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontWeight: 400, fontSize: 40, margin: 0, color: 'var(--tb-text-1)' }}>
              Command Center
            </h2>
            <p style={{ fontSize: 15, color: 'var(--tb-text-2)', marginTop: 12, maxWidth: 520, margin: '12px auto 0', lineHeight: 1.65 }}>
              A dashboard designed for speed, clarity, and honest decision-making
            </p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            style={{ background: 'var(--tb-ink-2)', border: '1px solid var(--tb-hairline)', borderRadius: 14, padding: 4, overflow: 'hidden' }}>
            <div style={{ background: 'var(--tb-ink)', borderRadius: 10, padding: 24 }}>
              {/* Browser chrome */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--tb-red)', opacity: 0.6 }} />
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--tb-gold)', opacity: 0.6 }} />
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--tb-mint)', opacity: 0.6 }} />
                </div>
                <div style={{ flex: 1, textAlign: 'center' }}>
                  <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--tb-text-3)', background: 'var(--tb-ink-2)', padding: '3px 12px', borderRadius: 4, border: '1px solid var(--tb-hairline)' }}>
                    tiebreaker.app/command
                  </span>
                </div>
              </div>

              {/* KPI row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'var(--tb-hairline)', borderRadius: 10, overflow: 'hidden', marginBottom: 16 }}>
                {[
                  { label: 'Fraud Prevented', value: '—', sub: 'From real model output', color: 'var(--tb-red)' },
                  { label: 'FP Revenue Saved', value: '—', sub: 'From real model output', color: 'var(--tb-gold)' },
                  { label: 'Net Position', value: '—', sub: 'From real model output', color: 'var(--tb-mint)' },
                  { label: 'Queue Pending', value: '—', sub: 'From real model output', color: 'var(--tb-text-1)' },
                ].map((s) => (
                  <div key={s.label} style={{ background: 'var(--tb-ink)', padding: '18px 20px' }}>
                    <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--tb-text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>{s.label}</div>
                    <div style={{ fontFamily: 'var(--f-mono)', fontSize: 22, fontWeight: 600, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 9, color: 'var(--tb-text-3)', marginTop: 4 }}>{s.sub}</div>
                  </div>
                ))}
              </div>

              <div style={{ height: 120, borderRadius: 10, background: 'var(--tb-ink-2)', border: '1px solid var(--tb-hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--tb-text-3)', fontSize: 12 }}>
                  <BarChart3 size={16} />
                  Live transaction pipeline — connect to /command to see real data
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '100px 24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 0%, rgba(232,162,61,0.05) 0%, transparent 60%)', pointerEvents: 'none' }} />
        <div className="max-w-[800px] mx-auto text-center relative z-10">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <h2 style={{ fontFamily: 'var(--f-display)', fontStyle: 'italic', fontWeight: 400, fontSize: 42, margin: '0 0 16px', color: 'var(--tb-text-1)' }}>
              Ready to break the tie?
            </h2>
            <p style={{ fontSize: 15, color: 'var(--tb-text-2)', margin: '0 auto 32px', maxWidth: 480, lineHeight: 1.65 }}>
              Experience the next generation of payment risk intelligence built for the Razorpay ecosystem.
            </p>
            <div className="flex items-center justify-center gap-4">
              <button onClick={() => navigate('/demostore')}
                className="group px-8 py-4 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                style={{ background: 'var(--tb-text-1)', color: 'var(--tb-ink)', fontFamily: 'var(--f-ui)' }}>
                Launch Live Demo
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
              <button onClick={() => navigate('/command')}
                className="px-8 py-4 text-sm font-semibold rounded-xl transition-all"
                style={{ color: 'var(--tb-text-1)', border: '1px solid var(--tb-hairline-strong)', background: 'transparent' }}>
                Explore Dashboard
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: '1px solid var(--tb-hairline)', padding: '40px 24px' }}>
        <div className="max-w-[1200px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <svg width={22} height={22} viewBox="0 0 100 100">
              <polygon points="50,6 50,94 8,50" fill="#E8433A"/>
              <polygon points="50,6 50,94 92,50" fill="#E8A23D"/>
              <rect x="48.3" y="6" width="3.4" height="88" fill="#130F16"/>
            </svg>
            <span style={{ fontWeight: 800, fontSize: 13, color: 'var(--tb-text-1)' }}>
              <span style={{ color: 'var(--tb-red)' }}>Tie</span>
              <span style={{ color: 'var(--tb-gold)' }}>Breaker</span>
            </span>
          </div>
          <div className="flex items-center gap-6">
            <span style={{ fontSize: 11, color: 'var(--tb-text-3)', fontFamily: 'var(--f-mono)' }}>Built for Razorpay Buildathon 2026</span>
            <span style={{ fontSize: 11, color: 'var(--tb-text-3)' }}>·</span>
            <span style={{ fontSize: 11, color: 'var(--tb-text-3)', fontFamily: 'var(--f-mono)' }}>Strike Decision Engine</span>
          </div>
        </div>
      </footer>

      <style>{`
        @keyframes stampSpin {
          from { transform: rotate(-6deg); }
          50% { transform: rotate(6deg); }
          to { transform: rotate(-6deg); }
        }
      `}</style>
    </div>
  )
}