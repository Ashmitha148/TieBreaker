import { useEffect, useState } from 'react'
import { API_URL } from '../config'

export default function Configuration() {
  const [cfg, setCfg] = useState<any>(null)
  const [edited, setEdited] = useState<any>({})

  useEffect(() => {
    fetch(`${API_URL}/api/config`).then(r => r.json()).then(d => {
      setCfg(d.current)
      setEdited(d.current)
    })
  }, [])

  if (!cfg) return <div className="p-10 text-center text-gray-400">Loading...</div>

  const update = (key: string, val: number) => setEdited({ ...edited, [key]: val })

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-cyan-400">Configuration</h1>
      <div className="bg-[#131a2b] p-5 rounded border border-gray-800 space-y-4">
        {Object.entries(edited).map(([key, val]: [string, any]) => (
          <div key={key} className="flex justify-between items-center">
            <span className="text-sm text-gray-300">{key.replace(/_/g, ' ')}</span>
            <input type="number" step="0.01" value={val} onChange={e => update(key, Number(e.target.value))} className="bg-[#0f1525] border border-gray-700 rounded px-3 py-1 text-right font-mono text-cyan-400 w-32" />
          </div>
        ))}
        <div className="pt-4 border-t border-gray-800">
          <button onClick={() => fetch(`${API_URL}/api/config`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(edited)})} className="bg-cyan-900 text-cyan-300 px-4 py-2 rounded text-sm font-bold hover:bg-cyan-800">
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  )
}