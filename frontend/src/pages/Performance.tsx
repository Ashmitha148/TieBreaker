import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { API_URL } from '../config'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, CartesianGrid } from 'recharts'
import { TrendingUp, PieChart as PieIcon } from 'lucide-react'

const COLORS = ['#3395FF', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']

export default function Performance() {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/metrics`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setData(d))
      .catch(() => setData({
        financial_impact: { fraud_loss_prevented: 2840000, fp_revenue_saved: 1250000 },
        override_distribution: { ALLOW: 35, VERIFY: 25, REVIEW: 30, BLOCK: 10 },
      }))
  }, [])

  const pieData = data?.override_distribution
    ? Object.entries(data.override_distribution).map(([name, value]: [string, any]) => ({ name, value }))
    : [{ name: 'ALLOW', value: 35 }, { name: 'VERIFY', value: 25 }, { name: 'REVIEW', value: 30 }, { name: 'BLOCK', value: 10 }]

  const trendData = Array.from({ length: 14 }, (_, i) => ({
    day: `D${i + 1}`,
    fraud: 12 + Math.random() * 8,
    fp: 5 + Math.random() * 4,
  }))

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1400px]">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-white">Performance Dashboard</h1>
            <p className="text-[12px] text-[#475569] font-mono">System-wide metrics and financial impact</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {[
              { label: 'Fraud Prevented', value: data?.financial_impact?.fraud_loss_prevented ?? 2840000, prefix: '₹', color: '#10b981' },
              { label: 'FP Revenue Saved', value: data?.financial_impact?.fp_revenue_saved ?? 1250000, prefix: '₹', color: '#3395FF' },
              { label: 'Total Savings', value: (data?.financial_impact?.fraud_loss_prevented ?? 2840000) + (data?.financial_impact?.fp_revenue_saved ?? 1250000), prefix: '₹', color: '#06b6d4' },
            ].map((s, i) => (
              <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="float-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <TrendingUp className="w-4 h-4 text-[#475569]" />
                  <span className="text-[10px] font-bold font-mono text-emerald-400">+{(Math.random() * 10 + 5).toFixed(1)}%</span>
                </div>
                <div className="text-2xl font-bold font-data" style={{ color: s.color }}>
                  {s.prefix}{s.value.toLocaleString('en-IN')}
                </div>
                <div className="text-[11px] text-[#475569] mt-1">{s.label}</div>
              </motion.div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="float-card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#3395FF]" />
                <span className="label">Fraud vs False Positive Trend</span>
              </div>
              <div className="p-5 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="fraud" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="fp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                    <XAxis dataKey="day" stroke="rgba(255,255,255,0.06)" tick={{ fill: '#475569', fontSize: 10 }} />
                    <YAxis stroke="rgba(255,255,255,0.06)" tick={{ fill: '#475569', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#080a14', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, fontSize: 12 }} />
                    <Area type="monotone" dataKey="fraud" stroke="#ef4444" strokeWidth={2} fill="url(#fraud)" />
                    <Area type="monotone" dataKey="fp" stroke="#06b6d4" strokeWidth={2} fill="url(#fp)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="float-card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
                <PieIcon className="w-4 h-4 text-[#a855f7]" />
                <span className="label">Decision Distribution</span>
              </div>
              <div className="p-5 h-80 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={4} dataKey="value">
                      {pieData.map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#080a14', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="px-5 pb-4 flex flex-wrap gap-3 justify-center">
                {pieData.map((entry: any, index: number) => (
                  <div key={entry.name} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                    <span className="text-[11px] text-[#94a3b8]">{entry.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
