import { useEffect, useState } from 'react'
import { API_URL } from '../config'

export default function PerformanceDashboard() {
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/metrics`).then(r => r.json()).then(setMetrics)
  }, [])

  if (!metrics) return <div className="p-10 text-center text-gray-400">Loading...</div>

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-cyan-400">Performance Dashboard</h1>
      <div className="text-xs text-amber-500 mb-4">⚠️ {metrics.disclaimer}</div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Fraud PR-AUC</div>
          <div className="text-2xl font-mono text-cyan-400">{metrics.fraud_pr_auc || 'N/A'}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Fraud Precision</div>
          <div className="text-2xl font-mono text-emerald-400">{metrics.fraud_precision || 'N/A'}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Fraud Recall</div>
          <div className="text-2xl font-mono text-amber-400">{metrics.fraud_recall || 'N/A'}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Fraud F1</div>
          <div className="text-2xl font-mono text-red-400">{metrics.fraud_f1 || 'N/A'}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">FP PR-AUC</div>
          <div className="text-2xl font-mono text-cyan-400">{metrics.fp_pr_auc || 'N/A'}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">FP Precision</div>
          <div className="text-2xl font-mono text-emerald-400">{metrics.fp_precision || 'N/A'}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">FP Recall</div>
          <div className="text-2xl font-mono text-amber-400">{metrics.fp_recall || 'N/A'}</div>
        </div>
      </div>

      <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
        <h3 className="text-sm font-bold mb-3 text-gray-400 uppercase">Financial Impact (Synthetic)</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-gray-400 text-xs">Baseline Loss</div>
            <div className="text-xl font-mono text-red-400">₹12.5L</div>
          </div>
          <div>
            <div className="text-gray-400 text-xs">TieBreaker Loss</div>
            <div className="text-xl font-mono text-emerald-400">₹9.8L</div>
          </div>
          <div>
            <div className="text-gray-400 text-xs">Saved</div>
            <div className="text-xl font-mono text-cyan-400">₹2.7L (21.6%)</div>
          </div>
        </div>
      </div>
    </div>
  )
}