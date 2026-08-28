import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, Shield, Brain, TrendingDown, ArrowRight, Zap, BarChart3, AlertTriangle } from 'lucide-react'

export default function LandingPage() {
  const [typed, setTyped] = useState('')
  const fullText = 'Cost-Aware Risk Intelligence'

  useEffect(() => {
    let i = 0
    const timer = setInterval(() => {
      if (i <= fullText.length) {
        setTyped(fullText.slice(0, i))
        i++
      } else {
        clearInterval(timer)
      }
    }, 50)
    return () => clearInterval(timer)
  }, [])

  const stats = [
    { label: 'Fraud Detected', value: '847', icon: Shield, color: 'text-red-400' },
    { label: 'Money Saved', value: '₹2.7L', suffix: '/mo', icon: TrendingDown, color: 'text-emerald-400' },
    { label: 'Review Time', value: '4.2', suffix: 'min', icon: Activity, color: 'text-cyan-400' },
    { label: 'Accuracy', value: '84.5', suffix: '%', icon: Brain, color: 'text-amber-400' },
  ]

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: `linear-gradient(rgba(34,211,238,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.3) 1px, transparent 1px)`,
        backgroundSize: '50px 50px'
      }} />
      <div className="absolute top-20 left-10 w-72 h-72 bg-cyan-500/5 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/40 border border-cyan-800/40 text-cyan-400 text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            RAZORPAY AI BUILDATHON 2026 — TRACK 02
          </div>
          <h1 className="text-5xl md:text-7xl font-black tracking-tight mb-4">
            <span className="text-white">Tie</span>
            <span className="text-cyan-400">Breaker</span>
          </h1>
          <p className="text-xl md:text-2xl text-gray-400 font-light h-8">
            {typed}<span className="animate-pulse text-cyan-400">|</span>
          </p>
          <p className="text-gray-500 mt-4 max-w-xl mx-auto text-sm leading-relaxed">
            Most fraud systems say YES or NO. TieBreaker asks: what does each decision <em>cost</em>? 
            A ₹50,000 block on a ₹5L LTV customer is a ₹5,05,000 mistake.
          </p>
          <div className="flex gap-4 justify-center mt-8">
            <Link to="/checkout" className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-semibold text-sm transition-all flex items-center gap-2 shadow-lg shadow-cyan-900/30">
              <Zap size={16} /> Launch Demo Checkout
            </Link>
            <Link to="/command" className="px-6 py-3 bg-[#131a2b] hover:bg-[#1a2332] text-gray-300 border border-gray-700 rounded-lg font-semibold text-sm transition-all flex items-center gap-2">
              <BarChart3 size={16} /> Command Center
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {stats.map((s) => (
            <div key={s.label} className="bg-[#131a2b] border border-gray-800/60 rounded-xl p-5 hover:border-gray-700 transition-all">
              <s.icon size={20} className={`${s.color} mb-3`} />
              <div className={`text-3xl font-mono font-bold ${s.color}`}>{s.value}</div>
              <div className="text-gray-500 text-xs mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
          {[
            { title: 'Decision Story', desc: 'See exactly why ALLOW, VERIFY, REVIEW, or BLOCK wins — with real ₹ costs.', icon: Brain, color: 'cyan' },
            { title: 'What-If Simulator', desc: 'Drag sliders. Watch costs recalculate live. Understand your risk surface.', icon: Activity, color: 'amber' },
            { title: 'Queue Oracle', desc: 'Analysts work top-down by money impact, not just fraud score.', icon: BarChart3, color: 'emerald' },
          ].map((f) => (
            <div key={f.title} className="bg-[#131a2b] border border-gray-800/60 rounded-xl p-6 hover:border-gray-700 transition-all group">
              <div className={`w-10 h-10 rounded-lg bg-${f.color}-950/50 border border-${f.color}-800/40 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <f.icon size={18} className={`text-${f.color}-400`} />
              </div>
              <h3 className="font-bold text-white mb-2">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        <div className="bg-gradient-to-r from-cyan-950/30 to-amber-950/20 border border-gray-800 rounded-2xl p-8 text-center">
          <AlertTriangle size={24} className="text-cyan-400 mx-auto mb-3" />
          <h3 className="text-xl font-bold text-white mb-2">Built for Razorpay Scale</h3>
          <p className="text-gray-400 text-sm mb-4">Real Test Mode payments. Real webhooks. Real decisions.</p>
          <Link to="/checkout" className="text-cyan-400 text-sm font-medium hover:text-cyan-300 flex items-center justify-center gap-1">
            Try it <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  )
}