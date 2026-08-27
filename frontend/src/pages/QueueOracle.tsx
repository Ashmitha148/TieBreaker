import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../config'

export default function QueueOracle() {
  const [queue, setQueue] = useState<any[]>([])
  const [view, setView] = useState<'fraud' | 'loss' | 'oracle'>('oracle')

  useEffect(() => {
    fetch(`${API_URL}/api/queue`).then(r => r.json()).then(d => setQueue(d.queue))
  }, [])

  const sorted = [...queue].sort((a, b) => {
    if (view === 'fraud') return b.fraud_prob - a.fraud_prob
    if (view === 'loss') return b.expected_loss - a.expected_loss
    return b.impact_score - a.impact_score
  })

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-4 text-cyan-400">Queue Oracle</h1>
      <div className="flex gap-2 mb-4">
        {(['fraud', 'loss', 'oracle'] as const).map(v => (
          <button key={v} onClick={() => setView(v)} className={`px-3 py-1 rounded text-xs font-bold ${view === v ? 'bg-cyan-900 text-cyan-300 border border-cyan-400' : 'bg-[#131a2b] text-gray-400 border border-gray-700'}`}>
            {v === 'fraud' ? 'Fraud Score View' : v === 'loss' ? 'Expected Loss View' : 'Oracle View'}
          </button>
        ))}
      </div>
      <div className="bg-[#131a2b] rounded border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#1a2332] text-gray-400 text-left">
            <tr><th className="p-3">Rank</th><th className="p-3">Transaction</th><th className="p-3">Amount</th><th className="p-3">Fraud %</th><th className="p-3">Expected Loss</th><th className="p-3">Impact</th><th className="p-3">Action</th></tr>
          </thead>
          <tbody>
            {sorted.map((tx, i) => (
              <tr key={tx.transaction_id} className="border-t border-gray-800 hover:bg-[#1a2332]">
                <td className="p-3 font-mono text-cyan-400">#{i+1}</td>
                <td className="p-3 font-mono"><Link to={`/transaction/${tx.transaction_id}`} className="text-cyan-400 hover:underline">{tx.transaction_id}</Link></td>
                <td className="p-3 font-mono">₹{tx.amount.toLocaleString('en-IN')}</td>
                <td className="p-3 font-mono text-red-400">{(tx.fraud_prob*100).toFixed(1)}%</td>
                <td className="p-3 font-mono">₹{Math.round(tx.expected_loss).toLocaleString('en-IN')}</td>
                <td className="p-3 font-mono text-amber-400">₹{Math.round(tx.impact_score).toLocaleString('en-IN')}</td>
                <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${tx.recommended_action === 'BLOCK' ? 'bg-red-900 text-red-300' : tx.recommended_action === 'REVIEW' ? 'bg-white/10 text-white' : 'bg-cyan-900 text-cyan-300'}`}>{tx.recommended_action}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}