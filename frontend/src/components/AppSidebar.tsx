import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, CreditCard, ListOrdered, Brain,
  BarChart3, Settings, ShieldCheck, ChevronLeft, ChevronRight
} from 'lucide-react'
import Logo from './Logo'

const links = [
  { path: '/command', label: 'Command Center', icon: LayoutDashboard },
  { path: '/checkout', label: 'Checkout Demo', icon: CreditCard },
  { path: '/queue', label: 'Queue Oracle', icon: ListOrdered },
  { path: '/learning', label: 'Override Learning', icon: Brain },
  { path: '/performance', label: 'Performance', icon: BarChart3 },
  { path: '/config', label: 'System Config', icon: Settings },
  { path: '/audit', label: 'Audit Trail', icon: ShieldCheck },
]

export default function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="fixed left-0 top-0 bottom-0 z-40 bg-[#03040a]/90 backdrop-blur-xl border-r border-white/[0.06] flex flex-col"
      style={{ width: collapsed ? 64 : 210 }}
    >
      <div className="h-16 flex items-center px-4 border-b border-white/[0.06]">
        <Link to="/" className="flex items-center">
          <Logo size={28} showText={!collapsed} textClassName="text-sm ml-2.5" />
        </Link>
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1">
        {links.map((link) => {
          const Icon = link.icon
          const active = location.pathname === link.path
          return (
            <Link
              key={link.path}
              to={link.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[12px] font-medium transition-all ${
                active
                  ? 'bg-[#3395FF]/10 text-[#3395FF] border border-[#3395FF]/20'
                  : 'text-[#94a3b8] hover:text-white hover:bg-white/[0.03]'
              }`}
              title={collapsed ? link.label : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{link.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="p-2 border-t border-white/[0.06]">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center py-2 rounded-lg text-[#475569] hover:text-white hover:bg-white/[0.03] transition-all"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </motion.aside>
  )
}
