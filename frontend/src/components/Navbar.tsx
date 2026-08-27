import { Link, useLocation } from 'react-router-dom'

export default function Navbar() {
  const loc = useLocation()
  const nav = [
    { path: '/', label: 'Demo Checkout' },
    { path: '/command', label: 'Command Center' },
    { path: '/transaction/TXN-COUNTER-001', label: 'Deep Dive' },
  ]
  return (
    <nav className="bg-[#0f1525] border-b border-gray-800 px-6 py-3 flex gap-6 text-sm font-medium items-center flex-wrap">
      <span className="text-cyan-400 font-bold mr-4">TIEBREAKER</span>
      {nav.map((n) => (
        <Link key={n.path} to={n.path}
          className={loc.pathname === n.path ? 'text-cyan-400' : 'text-gray-400 hover:text-gray-200'}>
          {n.label}
        </Link>
      ))}
      <span className="ml-auto text-amber-500 text-xs font-mono">RAZORPAY TEST MODE — NO REAL MONEY</span>
    </nav>
  )
}