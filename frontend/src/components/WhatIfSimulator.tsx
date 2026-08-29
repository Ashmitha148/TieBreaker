import { useState } from 'react'
import { motion } from 'framer-motion'
import { API_URL, apiHeaders } from '../config'

interface Props {
  baseAmount: number
  baseLtv: number
}

export default function WhatIfSimulator({ baseAmount, baseLtv }: Props) {
  const [fraudOverride, setFraudOverride] = useState<number | null>(null)
  const [fpOverride, setFpOverride] = useState<number | null>(null)
  const [useFraudOverride, setUseFraudOverride] = useState(false)
  const [useFpOverride, setUseFpOverride] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const runSimulation = async () => {
    setLoading(true)
    setError(null)
    try {
      const body: Record<string, unknown> = {
        amount: baseAmount,
        ltv: baseLtv,
      }
      if (useFraudOverride && fraudOverride !== null) {
        body.override_fraud_prob = fraudOverride
      }
      if (useFpOverride && fpOverride !== null) {
        body.override_fp_prob = fpOverride
      }
      const res = await fetch(`${API_URL}/api/what-if`, {
        method: 'POST',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const detail = await res.text()
        throw new Error(detail || `HTTP ${res.status}`)
      }
      setResult(await res.json())
    } catch (e: any) {
      setResult(null)
      setError(e?.message || 'What-if request failed')
    } finally {
      setLoading(false)
    }
  }

  const rec = result?.decision?.recommended_action
  const losses = result?.financial_analysis?.losses_by_action || {}
  const actionColors: Record<string, string> = {
    ALLOW: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400',
    VERIFY: 'bg-cyan-500/10 border-cyan-500/25 text-cyan-400',
    REVIEW: 'bg-amber-500/10 border-amber-500/25 text-amber-400',
    BLOCK: 'bg-rose-500/10 border-rose-500/25 text-rose-400',
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="flex items-center gap-2 text-[12px] mb-2 text-[#94a3b8]">
          <input type="checkbox" checked={useFraudOverride} onChange={(e) => setUseFraudOverride(e.target.checked)} />
          Override fraud probability
        </label>
        <div className="flex justify-between text-[12px] mb-2">
          <span className="text-[#94a3b8]">Fraud Probability</span>
          <span className="font-mono font-bold text-white">{((fraudOverride ?? 0.5) * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range" min="0" max="100" value={(fraudOverride ?? 0.5) * 100}
          disabled={!useFraudOverride}
          onChange={(e) => setFraudOverride(Number(e.target.value) / 100)}
          className="w-full h-1.5 bg-white/[0.04] rounded-full appearance-none cursor-pointer accent-[#3395FF]"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-[12px] mb-2 text-[#94a3b8]">
          <input type="checkbox" checked={useFpOverride} onChange={(e) => setUseFpOverride(e.target.checked)} />
          Override false-positive probability
        </label>
        <div className="flex justify-between text-[12px] mb-2">
          <span className="text-[#94a3b8]">False Positive Probability</span>
          <span className="font-mono font-bold text-white">{((fpOverride ?? 0.2) * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range" min="0" max="50" value={(fpOverride ?? 0.2) * 100}
          disabled={!useFpOverride}
          onChange={(e) => setFpOverride(Number(e.target.value) / 100)}
          className="w-full h-1.5 bg-white/[0.04] rounded-full appearance-none cursor-pointer accent-[#a855f7]"
        />
      </div>

      <button
        onClick={runSimulation}
        disabled={loading}
        className="w-full py-2.5 rounded-xl bg-[#3395FF]/15 border border-[#3395FF]/30 text-[#3395FF] text-xs font-bold"
      >
        {loading ? 'Running…' : 'Run what-if'}
      </button>

      {error && <div className="text-[12px] text-rose-400">{error}</div>}

      {result && (
        <>
          <div className="text-[11px] text-[#94a3b8] font-mono">
            fraud={result.model_inference?.fraud_probability} fp={result.model_inference?.fp_probability}
            {result.model_inference?.partial_override_note ? ` — ${result.model_inference.partial_override_note}` : ''}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(losses).map(([action, loss]) => (
              <motion.div
                key={action}
                className={`p-3 rounded-xl border ${rec === action ? 'bg-[#3395FF]/5' : 'bg-white/[0.02]'}`}
              >
                <div className="text-[10px] text-[#475569] uppercase font-bold">{action}</div>
                <div className="text-sm font-mono font-bold text-white mt-1">₹{Math.round(Number(loss)).toLocaleString('en-IN')}</div>
              </motion.div>
            ))}
          </div>
          {rec && (
            <div className={`text-center py-2.5 rounded-xl border text-xs font-bold ${actionColors[rec] || ''}`}>
              Recommended: {rec}
            </div>
          )}
        </>
      )}
    </div>
  )
}
