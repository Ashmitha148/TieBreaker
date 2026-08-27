import { useEffect, useState } from 'react'
import { API_URL } from '../config'

export default function SystemAudit() {
  const [logs, setLogs] = useState<any[]>([])

  useEffect(() => {
    fetch(`${API_URL}/api/audit`).then(r => r.json()).then(d => setLogs(d.logs))
  }, [])

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-cyan-400">System Audit</h1>
      <div className="bg-[#131a2b] rounded border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#1a2332] text-gray-400 text-left">
            <tr><th className="p-3">Timestamp</th><th className="p-3">User</th><th className="p-3">Action</th><th className="p-3">Entity</th><th className="p-3">Details</th></tr>
          </thead>
          <tbody>
            {logs.map((log, i) => (
              <tr key={i} className="border-t border-gray-800 hover:bg-[#1a2332]">
                <td className="p-3 font-mono text-gray-400">{new Date(log.timestamp).toLocaleString('en-IN')}</td>
                <td className="p-3 text-cyan-400">{log.user}</td>
                <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${log.action === 'OVERRIDE' ? 'bg-amber-900 text-amber-300' : log.action === 'DECISION' ? 'bg-cyan-900 text-cyan-300' : 'bg-gray-800 text-gray-400'}`}>{log.action}</span></td>
                <td className="p-3 font-mono">{log.entity_id}</td>
                <td className="p-3 text-gray-300">{log.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}