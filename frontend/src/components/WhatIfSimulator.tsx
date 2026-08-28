import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'

interface Props {
  baseAmount: number
  baseLtv: number
}

export default function WhatIfSimulator({ baseAmount, baseLtv }: Props) {
  const [fraudProb, setFraudProb] = useState(0.5)
  const [fpProb, setFpProb] = useState(0.2)

  const result = useMemo(() => {
    const fraudLoss = fraudProb * baseAmount * 2.5
    const _fpLoss = fpProb * baseLtv * 0.15
    void _fpLoss
    const frictionCost = 0.08 * baseAmount
    const analystCost = 100
    const reviewCost = fraudProb * baseAmount * 0.3 + fpProb * baseLtv * 0.05 + analystCost + frictionCost * 0.5
    const blockCost = fpProb * baseLtv + frictionCost

    const losses = {
      ALLOW: fraudLoss,
      VERIFY: fraudProb * baseAmount * 0.6 + frictionCost + fpProb * baseLtv * 0.1,
      REVIEW: reviewCost,
      BLOCK: blockCost,
    }
    const rec = Object.entries(losses).sort((a, b) => a[1] - b[1])[0][0]
    return { losses, recommended: rec }
  }, [fraudProb, fpProb, baseAmount, baseLtv])

  const actionColors: Record<string, string> = {
    ALLOW: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400',
    VERIFY: 'bg-cyan-500/10 border-cyan-500/25 text-cyan-400',
    REVIEW: 'bg-amber-500/10 border-amber-500/25 text-amber-400',
    BLOCK: 'bg-rose-500/10 border-rose-500/25 text-rose-400',
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between text-[12px] mb-2">
          <span className="text-[#94a3b8]">Fraud Probability</span>
          <span className="font-mono font-bold text-white">{(fraudProb * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range" min="0" max="100" value={fraudProb * 100}
          onChange={(e) => setFraudProb(Number(e.target.value) / 100)}
          className="w-full h-1.5 bg-white/[0.04] rounded-full appearance-none cursor-pointer accent-[#3395FF]"
        />
        <div className="flex justify-between text-[9px] text-[#475569] mt-1 font-mono">
          <span>0%</span><span>50%</span><span>100%</span>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-[12px] mb-2">
          <span className="text-[#94a3b8]">False Positive Probability</span>
          <span className="font-mono font-bold text-white">{(fpProb * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range" min="0" max="50" value={fpProb * 100}
          onChange={(e) => setFpProb(Number(e.target.value) / 100)}
          className="w-full h-1.5 bg-white/[0.04] rounded-full appearance-none cursor-pointer accent-[#a855f7]"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {Object.entries(result.losses).map(([action, loss]) => (
          <motion.div
            key={action}
            animate={{
              scale: result.recommended === action ? 1.02 : 1,
              borderColor: result.recommended === action ? 'rgba(51,149,255,0.3)' : 'rgba(255,255,255,0.06)',
            }}
            className={`p-3 rounded-xl border ${result.recommended === action ? 'bg-[#3395FF]/5' : 'bg-white/[0.02]'}`}
          >
            <div className="text-[10px] text-[#475569] uppercase font-bold">{action}</div>
            <div className="text-sm font-mono font-bold text-white mt-1">₹{Math.round(loss).toLocaleString('en-IN')}</div>
          </motion.div>
        ))}
      </div>

      <div className={`text-center py-2.5 rounded-xl border text-xs font-bold ${actionColors[result.recommended]}`}>
        Recommended: {result.recommended}
      </div>
    </div>
  )
}
