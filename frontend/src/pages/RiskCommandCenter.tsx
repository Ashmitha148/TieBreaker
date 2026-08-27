import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../config'

interface Tx { id: string; amount: number; is_fraud: number; is_flagged: number; merchant_category: string }

export default function RiskCommandCenter() {
  const [txs, setTxs] = useState<Tx[]>([])

  useEffect(() => {
    fetch(`${API_URL}/api/transactions`).then(r => r.json()).then(setTxs)
  }, [])

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-cyan-400">Live Risk Command Center</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Flagged</div>
          <div className="text-2xl font-mono text-amber-400">{txs.filter(t => t.is_flagged).length}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Fraud Detected</div>
          <div className="text-2xl font-mono text-red-400">{txs.filter(t => t.is_fraud).length}</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Avg Review Time</div>
          <div className="text-2xl font-mono text-cyan-400">4.2 min</div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <div className="text-gray-400 text-xs uppercase">Money Saved</div>
          <div className="text-2xl font-mono text-emerald-400">₹0</div>
        </div>
      </div>

      <div className="bg-[#131a2b] rounded border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#1a2332] text-gray-400 text-left">
            <tr><th className="p-3">Transaction ID</th><th className="p-3">Amount</th><th className="p-3">Category</th><th className="p-3">Risk</th><th className="p-3">Action</th></tr>
          </thead>
          <tbody>
            {txs.map(tx => (
              <tr key={tx.id} className="border-t border-gray-800 hover:bg-[#1a2332]">
                <td className="p-3 font-mono text-cyan-400"><Link to={`/transaction/${tx.id}`}>{tx.id}</Link></td>
                <td className="p-3 font-mono">₹{tx.amount.toLocaleString('en-IN')}</td>
                <td className="p-3">{tx.merchant_category}</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded text-xs ${tx.is_fraud ? 'bg-red-900 text-red-300' : 'bg-amber-900 text-amber-300'}`}>
                    {tx.is_fraud ? 'FRAUD' : 'FLAGGED'}
                  </span>
                </td>
                <td className="p-3"><Link to={`/transaction/${tx.id}`} className="text-cyan-400 hover:underline text-xs">Review →</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}