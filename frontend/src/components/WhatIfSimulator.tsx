import { useState } from 'react'

export default function WhatIfSimulator({ initialFraud = 0.5, initialFP = 0.2, initialAmount = 10000, initialLTV = 50000 }) {
  const [fraud, setFraud] = useState(initialFraud)
  const [fp, setFP] = useState(initialFP)
  const [amount, setAmount] = useState(initialAmount)
  const [ltv, setLTV] = useState(initialLTV)

  const allow = fraud * amount * 2.5
  const block = fp * (amount + ltv)
  const verify = 0.05 * amount + fraud * 0.30 * amount * 2.5
  const review = 100 + fraud * 0.15 * amount * 2.5

  const losses = { ALLOW: allow, VERIFY: verify, REVIEW: review, BLOCK: block }
  const rec = Object.entries(losses).sort((a, b) => a[1] - b[1])[0][0]

  const colors: any = { ALLOW: 'text-emerald-400', VERIFY: 'text-cyan-400', REVIEW: 'text-white', BLOCK: 'text-red-400' }

  return (
    <div className="bg-[#131a2b] p-5 rounded border border-gray-800 mt-4">
      <h3 className="text-md font-bold mb-4 text-cyan-400">What-If Simulator</h3>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="text-xs text-gray-400">Fraud Probability: {(fraud*100).toFixed(0)}%</label>
          <input type="range" min="0" max="100" value={fraud*100} onChange={e => setFraud(Number(e.target.value)/100)} className="w-full accent-cyan-400" />
        </div>
        <div>
          <label className="text-xs text-gray-400">FP Probability: {(fp*100).toFixed(0)}%</label>
          <input type="range" min="0" max="100" value={fp*100} onChange={e => setFP(Number(e.target.value)/100)} className="w-full accent-emerald-400" />
        </div>
        <div>
          <label className="text-xs text-gray-400">Amount: ₹{amount.toLocaleString('en-IN')}</label>
          <input type="range" min="1000" max="200000" step="1000" value={amount} onChange={e => setAmount(Number(e.target.value))} className="w-full accent-amber-400" />
        </div>
        <div>
          <label className="text-xs text-gray-400">LTV: ₹{ltv.toLocaleString('en-IN')}</label>
          <input type="range" min="5000" max="500000" step="5000" value={ltv} onChange={e => setLTV(Number(e.target.value))} className="w-full accent-purple-400" />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-center">
        {Object.entries(losses).map(([action, loss]: [string, any]) => (
          <div key={action} className={`p-2 rounded border ${action === rec ? 'border-cyan-400 bg-cyan-900/20' : 'border-gray-700'}`}>
            <div className="text-xs uppercase text-gray-400">{action}</div>
            <div className={`text-lg font-mono font-bold ${colors[action]}`}>₹{Math.round(loss).toLocaleString('en-IN')}</div>
            {action === rec && <div className="text-[10px] text-cyan-300">★ WINS</div>}
          </div>
        ))}
      </div>
    </div>
  )
}