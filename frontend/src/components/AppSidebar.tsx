import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, ShieldCheck, CreditCard, Eye, BarChart3,
  Settings, FileText, BookOpen, ChevronLeft, ChevronRight,
  BrainCircuit, Activity
} from 'lucide-react'
import { useState } from 'react'

const navGroups = [
  {
    label: 'OPERATE',
    items: [
      { label: 'Command Center', path: '/command', icon: LayoutDashboard },
      { label: 'Live Checkout', path: '/checkout', icon: CreditCard },
      { label: 'Shadow Mode', path: '/shadow', icon: Eye },
      { label: 'Queue Oracle', path: '/queue', icon: Activity },
    ],
  },
  {
    label: 'UNDERSTAND',
    items: [
      { label: 'Transaction Detail', path: '/transaction/demo', icon: FileText },
      { label: 'Performance', path: '/performance', icon: BarChart3 },
      { label: 'Learning Loop', path: '/learning', icon: BrainCircuit },
    ],
  },
  {
    label: 'GOVERN',
    items: [
      { label: 'Audit Log', path: '/audit', icon: ShieldCheck },
      { label: 'System Config', path: '/config', icon: Settings },
    ],
  },
]

export default function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="h-screen sticky top-0 flex flex-col shrink-0 transition-all duration-300"
      style={{
        width: collapsed ? 64 : 240,
        background: 'var(--tb-ink-2)',
        borderRight: '1px solid var(--tb-hairline)',
      }}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4" style={{ borderBottom: '1px solid var(--tb-hairline)' }}>
        <button onClick={() => navigate('/')} className="flex items-center gap-2.5 cursor-pointer" style={{ background: 'none', border: 'none' }}>
          <svg width={24} height={24} viewBox="0 0 100 100">
            <polygon points="50,6 50,94 8,50" fill="#E8433A"/>
            <polygon points="50,6 50,94 92,50" fill="#E8A23D"/>
            <rect x="48.3" y="6" width="3.4" height="88" fill="#130F16"/>
          </svg>
          {!collapsed && (
            <span style={{ fontWeight: 800, fontSize: 14, letterSpacing: '-0.01em', fontFamily: 'var(--f-ui)', whiteSpace: 'nowrap' }}>
              <span style={{ color: '#E8433A' }}>Tie</span>
              <span style={{ color: '#E8A23D' }}>Breaker</span>
            </span>
          )}
        </button>
      </div>

      {/* Nav Groups */}
      <div className="flex-1 overflow-y-auto py-4">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-5">
            {!collapsed && (
              <div className="px-4 pb-2 pt-3" style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--tb-text-3)', letterSpacing: '0.08em' }}>
                {group.label}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
              return (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer relative"
                  style={{
                    background: isActive ? 'var(--tb-ink-3)' : 'transparent',
                    color: isActive ? 'var(--tb-text-1)' : 'var(--tb-text-2)',
                    border: 'none',
                    borderRadius: 8,
                    margin: '0 8px',
                    width: collapsed ? 48 : 'calc(100% - 16px)',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  }}
                  onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.color = 'var(--tb-text-1)' }}
                  onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.color = 'var(--tb-text-2)' }}
                >
                  <Icon size={18} style={{ color: isActive ? 'var(--tb-gold)' : 'var(--tb-text-3)', flexShrink: 0 }} />
                  {!collapsed && (
                    <span className="truncate">{item.label}</span>
                  )}
                  {isActive && !collapsed && (
                    <div style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', width: 3, height: 16, background: 'var(--tb-gold)', borderRadius: '0 4px 4px 0' }} />
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </div>

      {/* Collapse Toggle */}
      <div className="h-12 flex items-center justify-center" style={{ borderTop: '1px solid var(--tb-hairline)' }}>
        <button onClick={() => setCollapsed(!collapsed)} style={{ background: 'none', border: 'none', color: 'var(--tb-text-3)', cursor: 'pointer', padding: 8 }}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </motion.aside>
  )
}