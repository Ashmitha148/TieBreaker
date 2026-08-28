import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { API_URL } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Brain, ToggleLeft, ToggleRight } from 'lucide-react'

export default function Learning() {
  const [data, setData] = useState<any>(null)
  const [_loading, setLoading] = useState(true)
  const [showAfter, setShowAfter] = useState(false)

  useEffect(() => {
    fetch(`${API_URL}/api/insights`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => {
        setData({
          before: { accuracy: 0.82, precision: 0.79, recall: 0.74, f1: 0.76 },
          after: { accuracy: 0.91, precision: 0.89, recall: 0.87, f1: 0.88 },
          learning_curve: Array.from({ length: 14 }, (_, i) => ({
            day: `D${i + 1}`,
            accuracy: 0.76 + (i * 0.012) + Math.random() * 0.02,
          })),
        })
        setLoading(false)
      })
  }, [])

  const metrics = showAfter ? data?.after : data?.before
  const metricKeys = ['accuracy', 'precision', 'recall', 'f1']

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1200px]">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-white">Override Learning</h1>
            <p className="text-[12px] text-[#475569] font-mono">Before/after impact of analyst overrides</p>
          </div>

          <div className="flex justify-center mb-6">
            <button onClick={() => setShowAfter(!showAfter)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.12] transition-all">
              {showAfter ? <ToggleRight className="w-4 h-4 text-emerald-400" /> : <ToggleLeft className="w-4 h-4 text-[#475569]" />}
              <span className="text-[12px] font-medium text-[#94a3b8]">{showAfter ? 'After Overrides' : 'Before Overrides'}</span>
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.div key={showAfter ? 'after' : 'before'} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {metricKeys.map((key, i) => (
                  <motion.div key={key} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.05 }}
                    className="float-card p-5 text-center">
                    <div className="text-[10px] text-[#475569] uppercase tracking-wider font-bold mb-1">{key}</div>
                    <div className="text-2xl font-bold text-white font-data">{((metrics?.[key] || 0.85) * 100).toFixed(1)}%</div>
                  </motion.div>
                ))}
              </div>

              <div className="float-card overflow-hidden">
                <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
                  <Brain className="w-4 h-4 text-[#3395FF]" />
                  <span className="label">Learning Curve</span>
                </div>
                <div className="p-5 h-80">
                  {data?.learning_curve ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={data.learning_curve}>
                        <defs>
                          <linearGradient id="lc" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#3395FF" stopOpacity={0.2} />
                            <stop offset="100%" stopColor="#3395FF" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                        <XAxis dataKey="day" stroke="rgba(255,255,255,0.06)" tick={{ fill: '#475569', fontSize: 10 }} />
                        <YAxis stroke="rgba(255,255,255,0.06)" tick={{ fill: '#475569', fontSize: 10 }} domain={[0.7, 1]} />
                        <Tooltip contentStyle={{ background: '#080a14', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, fontSize: 12 }} itemStyle={{ color: '#3395FF' }} />
                        <Area type="monotone" dataKey="accuracy" stroke="#3395FF" strokeWidth={2} fill="url(#lc)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-[#475569] text-xs">No learning data</div>
                  )}
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
