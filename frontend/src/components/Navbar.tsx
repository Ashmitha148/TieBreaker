import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { Menu, X, Zap } from 'lucide-react'

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const isLanding = location.pathname === '/'
  const isScrolled = true // Always show on landing for now

  const navLinks = [
    { label: 'Demo', path: '/demostore' },
    { label: 'Dashboard', path: '/command' },
    { label: 'Shadow Mode', path: '/shadow' },
    { label: 'Queue', path: '/queue' },
    { label: 'Learning', path: '/learning' },
  ]

  return (
    <>
      <motion.nav
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="fixed top-0 left-0 right-0 z-50"
        style={{
          background: 'rgba(19,15,22,0.86)',
          backdropFilter: 'blur(14px)',
          borderBottom: '1px solid var(--tb-hairline)',
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <button onClick={() => navigate('/')} className="flex items-center gap-2.5 cursor-pointer" style={{ background: 'none', border: 'none' }}>
            <svg width={24} height={24} viewBox="0 0 100 100">
              <polygon points="50,6 50,94 8,50" fill="#E8433A"/>
              <polygon points="50,6 50,94 92,50" fill="#E8A23D"/>
              <rect x="48.3" y="6" width="3.4" height="88" fill="#130F16"/>
            </svg>
            <span style={{ fontWeight: 800, fontSize: 15, letterSpacing: '-0.01em', fontFamily: 'var(--f-ui)' }}>
              <span style={{ color: '#E8433A' }}>Tie</span>
              <span style={{ color: '#E8A23D' }}>Breaker</span>
            </span>
          </button>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path
              return (
                <button
                  key={link.path}
                  onClick={() => navigate(link.path)}
                  className="relative px-3.5 py-2 text-[13px] font-semibold rounded-lg transition-all cursor-pointer"
                  style={{
                    background: isActive ? 'var(--tb-text-1)' : 'transparent',
                    color: isActive ? 'var(--tb-ink)' : 'var(--tb-text-2)',
                    border: 'none',
                    fontFamily: 'var(--f-ui)',
                  }}
                  onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.color = 'var(--tb-text-1)' }}
                  onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.color = 'var(--tb-text-2)' }}
                >
                  {link.label}
                </button>
              )
            })}
          </div>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-3">
            <button onClick={() => navigate('/demostore')}
              className="px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
              style={{ background: 'var(--tb-text-1)', color: 'var(--tb-ink)', border: 'none', fontFamily: 'var(--f-ui)' }}>
              <Zap size={14} />
              Try Demo
            </button>
          </div>

          {/* Mobile Toggle */}
          <button className="md:hidden p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} style={{ background: 'none', border: 'none', color: 'var(--tb-text-1)' }}>
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </motion.nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed inset-0 z-40 md:hidden pt-16"
            style={{ background: 'rgba(19,15,22,0.95)', backdropFilter: 'blur(20px)' }}
          >
            <div className="flex flex-col p-6 gap-2">
              {navLinks.map((link) => (
                <button key={link.path} onClick={() => { navigate(link.path); setMobileMenuOpen(false) }}
                  className="text-left px-4 py-3 rounded-lg text-sm font-semibold"
                  style={{ color: 'var(--tb-text-1)', background: location.pathname === link.path ? 'var(--tb-ink-2)' : 'transparent', border: 'none' }}>
                  {link.label}
                </button>
              ))}
              <button onClick={() => { navigate('/demostore'); setMobileMenuOpen(false) }}
                className="mt-4 px-4 py-3 rounded-lg text-sm font-bold text-center"
                style={{ background: 'var(--tb-text-1)', color: 'var(--tb-ink)', border: 'none' }}>
                Try Demo
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}