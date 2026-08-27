import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { API_URL } from '../config'
import WhatIfSimulator from '../components/WhatIfSimulator'

export default function TransactionDeepDive() {
  const { id } = useParams()
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/transactions/${id}`).then(r => r.json()).then(setData)
  }, [id])

  if (!data) return <div className="p-10 text-center text-gray-400">Loading...</div>
  if (data.detail) return <div className="p-10 text-center text-red-400">{data.detail}</div>

  const { transaction, fraud_prob, fp_prob, ltv, decision, savings_vs_baseline } = data
  const losses = decision?.losses || {}
  const rec = decision?.recommended_action || 'ALLOW'
  const colors: any = { ALLOW: 'bg-emerald-900 text-emerald-300', VERIFY: 'bg-cyan-900 text-cyan-300', REVIEW: 'bg-white/10 text-white', BLOCK: 'bg-red-900 text-red-300' }

  return (
    <div className="p-6 max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="space-y-4">
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase mb-2">Transaction</div>
          <div className="font-mono text-cyan-400 text-lg">{transaction?.transaction_id}</div>
          <div className="mt-2 text-3xl font-mono font-bold">₹{transaction?.amount?.toLocaleString('en-IN')}</div>
          <div className="text-gray-400 text-sm mt-1">{transaction?.merchant_category} • {transaction?.payment_method}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase mb-2">Synthetic Risk Context</div>
          <div className="text-xs text-amber-500 mb-2">⚠️ Synthetic data for demonstration</div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between"><span>Fraud Probability</span><span className="font-mono text-red-400">{(fraud_prob*100).toFixed(1)}%</span></div>
            <div className="flex justify-between"><span>False-Positive Prob</span><span className="font-mono text-emerald-400">{(fp_prob*100).toFixed(1)}%</span></div>
            <div className="flex justify-between"><span>Customer LTV</span><span className="font-mono text-cyan-400">₹{Math.round(ltv).toLocaleString('en-IN')}</span></div>
            <div className="flex justify-between"><span>Tenure</span><span className="font-mono">{transaction?.customer_tenure_days} days</span></div>
            <div className="flex justify-between"><span>Past 30d Txns</span><span className="font-mono">{transaction?.customer_tx_count_30d}</span></div>
          </div>
        </div>
      </div>

      <div className="md:col-span-2 space-y-4">
        <div className="bg-[#131a2b] p-5 rounded border border-gray-800">
          <h2 className="text-lg font-bold mb-4 text-white">Decision Story</h2>
          <div className="text-gray-400 text-xs uppercase font-bold mb-3">What does each action cost?</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {Object.entries(losses).map(([action, loss]: [string, any]) => (
              <div key={action} className={`p-3 rounded text-center border-2 ${action === rec ? 'border-cyan-400 ' + colors[action] : 'border-gray-700 bg-[#0f1525] text-gray-400'}`}>
                <div className="text-xs uppercase font-bold">{action}</div>
                <div className="text-xl font-mono font-bold mt-1">₹{Math.round(loss).toLocaleString('en-IN')}</div>
                {action === rec && <div className="text-xs mt-1 text-cyan-300">★ SELECTED</div>}
              </div>
            ))}
          </div>
          <div className="bg-[#0f1525] p-3 rounded border border-cyan-900/50">
            <div className="text-cyan-400 text-sm font-bold mb-1">Why {rec} wins:</div>
            <div className="text-gray-300 text-sm">{decision?.primary_reason}</div>
          </div>
          {savings_vs_baseline > 0 && (
            <div className="mt-3 text-emerald-400 text-sm font-bold">
              💰 Saved ₹{Math.round(savings_vs_baseline).toLocaleString('en-IN')} vs. threshold baseline ({data.baseline_action})
            </div>
          )}
          {decision?.is_counterintuitive && (
            <div className="mt-3 inline-block px-3 py-1 bg-amber-900/50 text-amber-400 text-xs font-bold rounded border border-amber-700">
              ⚡ COUNTERINTUITIVE — Fraud score is {(fraud_prob*100).toFixed(0)}% but {rec} saves more money
            </div>
          )}
        </div>
        <WhatIfSimulator initialFraud={fraud_prob} initialFP={fp_prob} initialAmount={transaction?.amount} initialLTV={ltv} />
      </div>
    </div>
  )
}