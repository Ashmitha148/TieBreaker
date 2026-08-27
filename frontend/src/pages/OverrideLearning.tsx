import { useEffect, useState } from 'react'
import { API_URL } from '../config'

export default function OverrideLearning() {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/insights`).then(r => r.json()).then(setData)
  }, [])

  if (!data) return <div className="p-10 text-center text-gray-400">Loading...</div>

  const { before, after, segments, net_improvement } = data

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-cyan-400">Override Learning</h1>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Loss Reduction', value: `${net_improvement.loss_reduction_pct}%`, color: 'text-emerald-400' },
          { label: 'Friction Reduction', value: `${net_improvement.friction_reduction_pct}%`, color: 'text-cyan-400' },
          { label: 'Review Efficiency', value: `${net_improvement.review_efficiency_pct}%`, color: 'text-amber-400' },
        ].map(m => (
          <div key={m.label} className="bg-[#131a2b] p-4 rounded border border-gray-800">
            <div className="text-gray-400 text-xs uppercase">{m.label}</div>
            <div className={`text-2xl font-mono font-bold ${m.color}`}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
          <h3 className="text-sm font-bold mb-3 text-gray-400 uppercase">BEFORE TieBreaker</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span>False Decline Rate</span><span className="font-mono text-red-400">{before.false_decline_rate}%</span></div>
            <div className="flex justify-between"><span>Fraud Capture</span><span className="font-mono text-amber-400">{before.fraud_capture_rate}%</span></div>
            <div className="flex justify-between"><span>Avg Review Time</span><span className="font-mono">{before.avg_review_time} min</span></div>
            <div className="flex justify-between"><span>Monthly Loss</span><span className="font-mono text-red-400">₹{before.monthly_loss.toLocaleString('en-IN')}</span></div>
          </div>
        </div>
        <div className="bg-[#131a2b] p-4 rounded border border-cyan-900/50">
          <h3 className="text-sm font-bold mb-3 text-cyan-400 uppercase">AFTER TieBreaker</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span>False Decline Rate</span><span className="font-mono text-emerald-400">{after.false_decline_rate}%</span></div>
            <div className="flex justify-between"><span>Fraud Capture</span><span className="font-mono text-emerald-400">{after.fraud_capture_rate}%</span></div>
            <div className="flex justify-between"><span>Avg Review Time</span><span className="font-mono text-cyan-400">{after.avg_review_time} min</span></div>
            <div className="flex justify-between"><span>Monthly Loss</span><span className="font-mono text-emerald-400">₹{after.monthly_loss.toLocaleString('en-IN')}</span></div>
          </div>
        </div>
      </div>

      <div className="bg-[#131a2b] p-4 rounded border border-gray-800">
        <h3 className="text-sm font-bold mb-3 text-gray-400 uppercase">Segment Calibration</h3>
        <table className="w-full text-sm">
          <thead className="text-gray-400 text-left"><tr><th className="p-2">Segment</th><th className="p-2">Overrides</th><th className="p-2">Accuracy</th><th className="p-2">LTV Adj</th></tr></thead>
          <tbody>
            {segments.map((s: any, i: number) => (
              <tr key={i} className="border-t border-gray-800">
                <td className="p-2">{s.segment}</td>
                <td className="p-2 font-mono">{s.override_count}</td>
                <td className="p-2 font-mono text-emerald-400">{(s.accuracy*100).toFixed(0)}%</td>
                <td className="p-2 font-mono text-cyan-400">{s.ltv_adjustment.toFixed(2)}x</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}