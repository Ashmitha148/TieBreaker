import { useState } from 'react'
import { motion } from 'framer-motion'
import AppSidebar from '../components/AppSidebar'
import StatusBar from '../components/StatusBar'
import { Save, RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'

interface ConfigField {
  key: string
  label: string
  value: number
  min: number
  max: number
  step: number
  desc: string
}

export default function Config() {
  const [configs, setConfigs] = useState<ConfigField[]>([
    { key: 'fraud_threshold', label: 'Fraud Threshold', value: 0.72, min: 0.1, max: 0.99, step: 0.01, desc: 'Minimum fraud probability to trigger review' },
    { key: 'fp_threshold', label: 'False Positive Threshold', value: 0.35, min: 0.1, max: 0.99, step: 0.01, desc: 'Maximum FP probability before allowing' },
    { key: 'review_cost', label: 'Analyst Review Cost (₹)', value: 100, min: 50, max: 500, step: 10, desc: 'Cost per manual review' },
    { key: 'fraud_multiplier', label: 'Fraud Loss Multiplier', value: 2.5, min: 1.0, max: 5.0, step: 0.1, desc: 'Expected loss multiplier for fraud' },
    { key: 'ltv_weight', label: 'LTV Weight', value: 0.15, min: 0.05, max: 0.5, step: 0.05, desc: 'Weight given to customer lifetime value' },
  ])

  const handleChange = (key: string, val: number) => {
    setConfigs(prev => prev.map(c => c.key === key ? { ...c, value: val } : c))
  }

  const handleSave = () => {
    toast.success('Configuration saved successfully')
  }

  const handleReset = () => {
    setConfigs([
      { key: 'fraud_threshold', label: 'Fraud Threshold', value: 0.72, min: 0.1, max: 0.99, step: 0.01, desc: 'Minimum fraud probability to trigger review' },
      { key: 'fp_threshold', label: 'False Positive Threshold', value: 0.35, min: 0.1, max: 0.99, step: 0.01, desc: 'Maximum FP probability before allowing' },
      { key: 'review_cost', label: 'Analyst Review Cost (₹)', value: 100, min: 50, max: 500, step: 10, desc: 'Cost per manual review' },
      { key: 'fraud_multiplier', label: 'Fraud Loss Multiplier', value: 2.5, min: 1.0, max: 5.0, step: 0.1, desc: 'Expected loss multiplier for fraud' },
      { key: 'ltv_weight', label: 'LTV Weight', value: 0.15, min: 0.05, max: 0.5, step: 0.05, desc: 'Weight given to customer lifetime value' },
    ])
    toast.success('Configuration reset to defaults')
  }

  return (
    <div className="relative z-10">
      <AppSidebar />
      <div className="ml-[210px] min-h-screen pb-8">
        <div className="pt-6 pb-8 px-6 max-w-[1000px]">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold text-white">System Configuration</h1>
              <p className="text-[12px] text-[#475569] font-mono">Tune model thresholds and cost parameters</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={handleReset} className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[0.08] text-[11px] font-bold text-[#94a3b8] hover:text-white hover:border-white/[0.15] transition-all">
                <RotateCcw className="w-3.5 h-3.5" /> Reset
              </button>
              <button onClick={handleSave} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gradient-to-r from-[#3395FF] to-[#2563eb] text-white text-[11px] font-bold hover:shadow-lg hover:shadow-[#3395FF]/25 transition-all">
                <Save className="w-3.5 h-3.5" /> Save
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {configs.map((cfg, i) => (
              <motion.div
                key={cfg.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="float-card p-5"
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-[13px] font-bold text-white">{cfg.label}</div>
                    <div className="text-[10px] text-[#475569] mt-0.5">{cfg.desc}</div>
                  </div>
                  <div className="text-sm font-bold font-data text-[#3395FF]">
                    {cfg.key.includes('cost') ? `₹${cfg.value}` : cfg.value}
                  </div>
                </div>
                <input
                  type="range"
                  min={cfg.min}
                  max={cfg.max}
                  step={cfg.step}
                  value={cfg.value}
                  onChange={(e) => handleChange(cfg.key, Number(e.target.value))}
                  className="w-full h-1.5 bg-white/[0.04] rounded-full appearance-none cursor-pointer accent-[#3395FF]"
                />
                <div className="flex justify-between text-[9px] text-[#475569] mt-1 font-mono">
                  <span>{cfg.min}</span>
                  <span>{cfg.max}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
      <StatusBar />
    </div>
  )
}
