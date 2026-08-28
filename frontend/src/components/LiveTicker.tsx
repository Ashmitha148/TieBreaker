import { useEffect, useState } from 'react'
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'

const demoItems = [
  { id: 'pay_LxK9mN2pQr', amount: '₹45,000', action: 'REVIEW', trend: 'up' },
  { id: 'pay_MnP2qR5sTu', amount: '₹1,20,000', action: 'ALLOW', trend: 'flat' },
  { id: 'pay_KjH7vW8xYz', amount: '₹89,000', action: 'BLOCK', trend: 'down' },
  { id: 'pay_QwE4tY1uIo', amount: '₹34,000', action: 'VERIFY', trend: 'flat' },
  { id: 'pay_ZxC1bN4vWx', amount: '₹5,67,000', action: 'REVIEW', trend: 'up' },
  { id: 'pay_AbC3dE7fGh', amount: '₹22,000', action: 'ALLOW', trend: 'flat' },
  { id: 'pay_FgH5iJ0kLm', amount: '₹1,50,000', action: 'REVIEW', trend: 'up' },
  { id: 'pay_KlM6nO9pQr', amount: '₹7,800', action: 'BLOCK', trend: 'down' },
]

export default function LiveTicker() {
  const [items, setItems] = useState(demoItems)

  useEffect(() => {
    const interval = setInterval(() => {
      setItems(prev => {
        const next = [...prev]
        next.push(next.shift()!)
        return next
      })
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const actionColors: Record<string, string> = {
    ALLOW: 'text-emerald-400',
    BLOCK: 'text-rose-400',
    REVIEW: 'text-amber-400',
    VERIFY: 'text-cyan-400',
  }

  const TrendIcon = ({ trend }: { trend: string }) => {
    if (trend === 'up') return <ArrowUpRight className="w-3 h-3 text-emerald-400" />
    if (trend === 'down') return <ArrowDownRight className="w-3 h-3 text-rose-400" />
    return <Minus className="w-3 h-3 text-[#475569]" />
  }

  return (
    <div className="bg-[#03040a]/60 border-b border-white/[0.06] py-2 overflow-hidden">
      <div className="ticker-wrap">
        <div className="ticker-content">
          {[...items, ...items].map((item, i) => (
            <span key={i} className="inline-flex items-center gap-2 mx-6">
              <span className="text-[10px] font-mono text-[#475569]">{item.id}</span>
              <span className="text-[11px] font-bold text-white">{item.amount}</span>
              <span className={`text-[10px] font-bold ${actionColors[item.action]}`}>{item.action}</span>
              <TrendIcon trend={item.trend} />
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
