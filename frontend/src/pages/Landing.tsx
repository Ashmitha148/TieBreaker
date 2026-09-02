import { useEffect, useState, useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import {
  Zap, Shield, Brain, ArrowRight, TrendingUp, Clock,
  CreditCard, Lock, Eye, BarChart3, ChevronDown, Sparkles
} from 'lucide-react'

function FloatingCard({ children, className = '', delay = 0, onClick }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.6, delay }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      onClick={onClick}
      className={`float-card glow-border p-5 ${className}`}
    >
      {children}
    </motion.div>
  )
}

function AnimatedCounter({ value, prefix = '', suffix = '' }: any) {
  const [count, setCount] = useState(0)
  const [hasStarted, setHasStarted] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasStarted) {
          setHasStarted(true)
        }
      },
      { threshold: 0.5 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [hasStarted])

  useEffect(() => {
    if (!hasStarted) return
    const duration = 2000
    const steps = 60
    const increment = value / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setCount(value)
        clearInterval(timer)
      } else {
        setCount(Math.floor(current))
      }
    }, duration / steps)
    return () => clearInterval(timer)
  }, [hasStarted, value])

  return <span ref={ref}>{prefix}{count.toLocaleString('en-IN')}{suffix}</span>
}

// Animated background particles
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let w = canvas.width = canvas.offsetWidth
    let h = canvas.height = canvas.offsetHeight

    const particles: { x: number; y: number; vx: number; vy: number; size: number; alpha: number }[] = []
    for (let i = 0; i < 40; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 2 + 1,
        alpha: Math.random() * 0.5 + 0.1,
      })
    }

    let animId: number
    const animate = () => {
      ctx.clearRect(0, 0, w, h)
      particles.forEach((p, i) => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0 || p.x > w) p.vx *= -1
        if (p.y < 0 || p.y > h) p.vy *= -1

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(51, 149, 255, ${p.alpha})`
        ctx.fill()

        // Connect nearby particles
        particles.slice(i + 1).forEach(p2 => {
          const dx = p.x - p2.x
          const dy = p.y - p2.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 120) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.strokeStyle = `rgba(51, 149, 255, ${0.08 * (1 - dist / 120)})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        })
      })
      animId = requestAnimationFrame(animate)
    }
    animate()

    const handleResize = () => {
      w = canvas.width = canvas.offsetWidth
      h = canvas.height = canvas.offsetHeight
    }
    window.addEventListener('resize', handleResize)
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.6 }}
    />
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const { scrollYProgress } = useScroll()
  const heroOpacity = useTransform(scrollYProgress, [0, 0.15], [1, 0])
  const heroY = useTransform(scrollYProgress, [0, 0.15], [0, -50])

  return (
    <div className="relative z-10">
      <Navbar />

      {/* HERO */}
      <section className="min-h-screen flex items-center justify-center pt-20 px-6 relative overflow-hidden">
        <ParticleField />
        <motion.div style={{ opacity: heroOpacity, y: heroY }} className="max-w-[1200px] w-full relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 1, ease: 'easeOut' }}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#3395FF]/10 border border-[#3395FF]/20 text-[11px] font-bold text-[#3395FF] mb-6"
              >
                <Sparkles className="w-3 h-3" />
                Razorpay Buildathon 2026 — Winner's Circle
              </motion.div>

              <h1 className="text-5xl lg:text-7xl font-bold text-white leading-[1.1] tracking-tight">
                The Future of<br />
                <span className="relative">
                  <span className="bg-gradient-to-r from-[#3395FF] via-[#7c3aed] to-[#a855f7] bg-clip-text text-transparent">
                    Payment Risk
                  </span>
                  <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" fill="none">
                    <motion.path
                      d="M2 8C50 2 100 2 150 8C200 14 250 14 298 8"
                      stroke="url(#underline)"
                      strokeWidth="3"
                      strokeLinecap="round"
                      initial={{ pathLength: 0 }}
                      animate={{ pathLength: 1 }}
                      transition={{ duration: 1.5, delay: 1 }}
                    />
                    <defs>
                      <linearGradient id="underline" x1="0" y1="0" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#3395FF" />
                        <stop offset="100%" stopColor="#a855f7" />
                      </linearGradient>
                    </defs>
                  </svg>
                </span>
              </h1>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="text-base text-[#94a3b8] mt-6 max-w-lg leading-relaxed"
              >
                TieBreaker uses <span className="text-white font-semibold">dual-model inference</span> to simultaneously 
                detect fraud and minimize false positives — saving millions in lost revenue while 
                keeping every transaction secure.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="flex items-center gap-3 mt-8"
              >
                <button
                  onClick={() => navigate('/checkout')}
                  className="group px-6 py-3.5 bg-gradient-to-r from-[#3395FF] to-[#7c3aed] text-white rounded-xl text-sm font-bold hover:shadow-2xl hover:shadow-[#3395FF]/30 transition-all flex items-center gap-2"
                >
                  Try Live Demo
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={() => navigate('/command')}
                  className="px-6 py-3.5 text-sm font-semibold text-white border border-white/[0.1] rounded-xl hover:border-[#3395FF]/40 hover:bg-[#3395FF]/5 transition-all"
                >
                  Command Center
                </button>
              </motion.div>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="flex items-center gap-6 mt-10"
              >
                {[
                  { icon: Shield, label: 'SOC 2 Ready' },
                  { icon: Lock, label: 'End-to-End Encrypted' },
                  { icon: Zap, label: '<50ms Latency' },
                ].map((item) => {
                  const Icon = item.icon
                  return (
                    <div key={item.label} className="flex items-center gap-2 text-[11px] text-[#475569]">
                      <Icon className="w-3.5 h-3.5 text-[#3395FF]" />
                      {item.label}
                    </div>
                  )
                })}
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.3, type: 'spring' }}
              className="relative hidden lg:block"
            >
              <div className="relative w-full aspect-square max-w-[520px] mx-auto">
                {/* Glow ring */}
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
                  className="absolute inset-[-20px] rounded-full border border-dashed border-white/[0.04]"
                />
                <motion.div
                  animate={{ rotate: -360 }}
                  transition={{ duration: 40, repeat: Infinity, ease: 'linear' }}
                  className="absolute inset-[-40px] rounded-full border border-dashed border-white/[0.03]"
                />

                {/* Center AI Node */}
                <motion.div
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 rounded-full bg-gradient-to-br from-[#3395FF] to-[#a855f7] flex items-center justify-center shadow-2xl shadow-[#3395FF]/40"
                >
                  <Brain className="w-12 h-12 text-white" />
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-[#3395FF] to-[#a855f7] blur-xl opacity-40" />
                </motion.div>

                {/* Legitimate Stream Card */}
                <motion.div
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                  className="absolute top-[15%] left-[10%] w-36 rounded-2xl bg-emerald-500/[0.08] border border-emerald-500/20 p-4 backdrop-blur-sm"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-wider">Legitimate</span>
                  </div>
                  <div className="text-lg font-bold text-white font-data">94.2%</div>
                  <div className="text-[9px] text-[#475569] mt-0.5">₹12.4Cr processed</div>
                </motion.div>

                {/* Fraud Stream Card */}
                <motion.div
                  animate={{ y: [0, 8, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
                  className="absolute bottom-[15%] right-[10%] w-36 rounded-2xl bg-rose-500/[0.08] border border-rose-500/20 p-4 backdrop-blur-sm"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />
                    <span className="text-[9px] font-bold text-rose-400 uppercase tracking-wider">Fraud</span>
                  </div>
                  <div className="text-lg font-bold text-white font-data">5.8%</div>
                  <div className="text-[9px] text-[#475569] mt-0.5">₹28L prevented</div>
                </motion.div>

                {/* Connection lines SVG */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 520 520">
                  <defs>
                    <linearGradient id="legitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#3395FF" stopOpacity="0.2" />
                    </linearGradient>
                    <linearGradient id="fraudGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#3395FF" stopOpacity="0.2" />
                    </linearGradient>
                  </defs>
                  <motion.path
                    d="M120 130 Q260 200 260 260"
                    stroke="url(#legitGrad)"
                    strokeWidth="2"
                    fill="none"
                    strokeDasharray="8 4"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
                  />
                  <motion.path
                    d="M400 390 Q260 320 260 260"
                    stroke="url(#fraudGrad)"
                    strokeWidth="2"
                    fill="none"
                    strokeDasharray="8 4"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse', delay: 0.5 }}
                  />
                </svg>

                {/* Floating mini transaction cards */}
                {[
                  { x: '75%', y: '20%', amount: '₹45,000', status: 'ALLOW', color: '#10b981', delay: 0 },
                  { x: '15%', y: '65%', amount: '₹1,20,000', status: 'REVIEW', color: '#f59e0b', delay: 0.5 },
                  { x: '70%', y: '70%', amount: '₹89,000', status: 'BLOCK', color: '#ef4444', delay: 1 },
                ].map((card, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1, y: [0, -6, 0] }}
                    transition={{
                      opacity: { delay: 1.5 + card.delay },
                      scale: { delay: 1.5 + card.delay },
                      y: { duration: 3 + i, repeat: Infinity, ease: 'easeInOut', delay: card.delay },
                    }}
                    className="absolute px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] backdrop-blur-sm"
                    style={{ left: card.x, top: card.y, transform: 'translate(-50%, -50%)' }}
                  >
                    <div className="text-[9px] font-mono text-[#475569]">pay_{Math.random().toString(36).slice(2, 6).toUpperCase()}</div>
                    <div className="text-[11px] font-bold text-white font-data">{card.amount}</div>
                    <div className="text-[8px] font-bold uppercase mt-0.5" style={{ color: card.color }}>{card.status}</div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2 }}
            className="flex justify-center mt-8"
          >
            <motion.button
              onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-[#475569] hover:text-white transition-colors"
            >
              <ChevronDown className="w-6 h-6" />
            </motion.button>
          </motion.div>
        </motion.div>
      </section>

      {/* STATS BAR */}
      <section className="py-16 px-6 border-y border-white/[0.06] relative">
        <div className="max-w-[1200px] mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { label: 'Fraud Prevented', value: 2840000, prefix: '₹', suffix: 'L+' },
            { label: 'Accuracy', value: 99.2, prefix: '', suffix: '%', decimals: 1 },
            { label: 'Latency', value: 12, prefix: '', suffix: 'ms' },
            { label: 'Transactions', value: 5000000, prefix: '', suffix: '+' },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <div className="text-4xl font-bold text-white font-data">
                <AnimatedCounter value={stat.value} prefix={stat.prefix} suffix={stat.suffix} />
              </div>
              <div className="text-[11px] text-[#475569] mt-2 uppercase tracking-widest font-bold">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="py-28 px-6">
        <div className="max-w-[1200px] mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <span className="text-[11px] font-bold text-[#3395FF] uppercase tracking-widest">Architecture</span>
            <h2 className="text-4xl font-bold text-white mt-3">How TieBreaker Works</h2>
            <p className="text-[15px] text-[#94a3b8] mt-4 max-w-lg mx-auto">
              Every transaction flows through a dual-stream intelligence pipeline
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8 relative">
            {/* Connection line */}
            <div className="hidden md:block absolute top-1/2 left-[16.67%] right-[16.67%] h-[1px] bg-gradient-to-r from-transparent via-[#3395FF]/20 to-transparent" />

            {[
              {
                step: '01',
                icon: CreditCard,
                title: 'Payment Initiated',
                desc: 'Customer completes checkout via UPI, Card, or NetBanking. Transaction data is captured in real-time with full device fingerprinting.',
                color: '#3395FF',
              },
              {
                step: '02',
                icon: Brain,
                title: 'Dual Model Inference',
                desc: 'Fraud Detection + False Positive models run in parallel on GPU clusters, scoring risk from both angles in under 20ms.',
                color: '#a855f7',
              },
              {
                step: '03',
                icon: Shield,
                title: 'Strike Decision Engine',
                desc: 'Cost-optimized decision engine picks the action with lowest expected financial loss — not just the highest accuracy.',
                color: '#10b981',
              },
            ].map((item, i) => {
              const Icon = item.icon
              return (
                <FloatingCard key={item.title} delay={i * 0.15} className="relative">
                  <div className="absolute -top-4 left-5 px-2 py-0.5 bg-[#03040a] border border-white/[0.08] rounded text-[10px] font-mono font-bold text-[#475569]">
                    {item.step}
                  </div>
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5 mt-2" style={{ backgroundColor: `${item.color}12` }}>
                    <Icon className="w-6 h-6" style={{ color: item.color }} />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-3">{item.title}</h3>
                  <p className="text-[13px] text-[#94a3b8] leading-relaxed">{item.desc}</p>
                </FloatingCard>
              )
            })}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="product" className="py-28 px-6 border-y border-white/[0.06]">
        <div className="max-w-[1200px] mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <span className="text-[11px] font-bold text-[#3395FF] uppercase tracking-widest">Capabilities</span>
            <h2 className="text-4xl font-bold text-white mt-3">Built for Scale</h2>
            <p className="text-[15px] text-[#94a3b8] mt-4 max-w-lg mx-auto">
              Infrastructure that payment processors trust at millions of transactions per day
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon: Eye, title: 'Counterintuitive Detection', desc: 'Flags high-fraud cases where REVIEW beats BLOCK to preserve customer LTV and merchant relationships.' },
              { icon: Clock, title: 'Real-Time Pipeline', desc: 'End-to-end decision in under 50ms with full audit trail, SHAP explanations, and model versioning.' },
              { icon: TrendingUp, title: 'Continuous Learning', desc: 'Analyst overrides feed back into model retraining via active learning, improving accuracy daily.' },
              { icon: BarChart3, title: 'Financial Impact', desc: 'Track rupees saved from fraud prevention and false-positive reduction with real-time counters.' },
              { icon: Lock, title: 'Analyst Override', desc: 'Human-in-the-loop review queue with priority scoring, impact analysis, and one-click actions.' },
              { icon: Zap, title: 'What-If Simulator', desc: 'Adjust fraud/FP probabilities in real-time to see how optimal decisions change before deploying.' },
            ].map((item, i) => {
              const Icon = item.icon
              return (
                <FloatingCard key={item.title} delay={i * 0.08}>
                  <div className="w-10 h-10 rounded-lg bg-[#3395FF]/10 flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-[#3395FF]" />
                  </div>
                  <h3 className="text-[15px] font-bold text-white mb-2">{item.title}</h3>
                  <p className="text-[12px] text-[#94a3b8] leading-relaxed">{item.desc}</p>
                </FloatingCard>
              )
            })}
          </div>
        </div>
      </section>

      {/* DASHBOARD PREVIEW */}
      <section className="py-28 px-6">
        <div className="max-w-[1200px] mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <span className="text-[11px] font-bold text-[#3395FF] uppercase tracking-widest">Interface</span>
            <h2 className="text-4xl font-bold text-white mt-3">Command Center</h2>
            <p className="text-[15px] text-[#94a3b8] mt-4 max-w-lg mx-auto">
              A dashboard designed for speed, clarity, and action
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="float-card glow-border p-1 overflow-hidden"
          >
            <div className="bg-[#03040a] rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                </div>
                <span className="text-[10px] text-[#475569] font-mono">TieBreaker Command Center v2.0.0</span>
              </div>
              <div className="grid grid-cols-4 gap-4 mb-6">
                {[
                  { label: 'Total Decisions', value: '1,247', trend: '+12.5%', color: 'text-emerald-400' },
                  { label: 'Fraud Prevented', value: '₹28.4L', trend: '+8.3%', color: 'text-emerald-400' },
                  { label: 'Override Rate', value: '3.2%', trend: '-2.1%', color: 'text-rose-400' },
                  { label: 'Avg Review', value: '4.2m', trend: '-0.4m', color: 'text-emerald-400' },
                ].map((s) => (
                  <div key={s.label} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <div className="text-[9px] text-[#475569] uppercase font-bold mb-1">{s.label}</div>
                    <div className="text-lg font-bold text-white font-data">{s.value}</div>
                    <div className={`text-[9px] font-mono mt-1 ${s.color}`}>{s.trend}</div>
                  </div>
                ))}
              </div>
              <div className="h-32 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-center">
                <div className="flex items-center gap-2 text-[#475569]">
                  <BarChart3 className="w-4 h-4" />
                  <span className="text-[11px]">Live transaction pipeline visualization</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-28 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#3395FF]/5 via-transparent to-transparent pointer-events-none" />
        <div className="max-w-[800px] mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl font-bold text-white mb-4">Ready to break the tie?</h2>
            <p className="text-[15px] text-[#94a3b8] mb-10 max-w-md mx-auto">
              Experience the next generation of payment risk intelligence built for the Razorpay ecosystem.
            </p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => navigate('/checkout')}
                className="group px-8 py-4 bg-gradient-to-r from-[#3395FF] to-[#a855f7] text-white rounded-xl text-sm font-bold hover:shadow-2xl hover:shadow-[#3395FF]/30 transition-all flex items-center gap-2"
              >
                Launch Live Demo
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
              <button
                onClick={() => navigate('/command')}
                className="px-8 py-4 text-sm font-semibold text-white border border-white/[0.1] rounded-xl hover:border-[#3395FF]/40 hover:bg-[#3395FF]/5 transition-all"
              >
                Explore Dashboard
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-white/[0.06] py-10 px-6">
        <div className="max-w-[1200px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#3395FF] to-[#a855f7] flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-[13px] font-bold text-white">TieBreaker</span>
          </div>
          <div className="flex items-center gap-6">
            <span className="text-[11px] text-[#475569]">Built for Razorpay Buildathon 2026</span>
            <span className="text-[11px] text-[#475569]">•</span>
            <span className="text-[11px] text-[#475569]">AI Payment Risk Intelligence</span>
          </div>
        </div>
      </footer>
    </div>
  )
}