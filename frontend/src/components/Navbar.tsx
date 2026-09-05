import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import Logo from './Logo'

const navLinks = [
  { label: 'Product', href: '#product' },
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'Dashboard', path: '/command' },
  { label: 'Docs', href: '#docs' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const handle = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', handle)
    return () => window.removeEventListener('scroll', handle)
  }, [])

  const handleNav = (item: any) => {
    if (item.path) {
      navigate(item.path)
    } else if (item.href) {
      const el = document.querySelector(item.href)
      if (el) el.scrollIntoView({ behavior: 'smooth' })
    }
    setMobileOpen(false)
  }

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled ? 'bg-[#03040a]/80 backdrop-blur-xl border-b border-white/[0.06]' : 'bg-transparent'
      }`}
    >
      <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/">
          <Logo size={32} showText={true} textClassName="text-base" />
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((item) => (
            <button
              key={item.label}
              onClick={() => handleNav(item)}
              className="text-[13px] text-[#94a3b8] hover:text-white transition-colors font-medium"
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={() => navigate('/command')}
            className="px-4 py-2 text-[13px] font-semibold text-white border border-white/[0.1] rounded-lg hover:border-[#3395FF]/30 hover:bg-[#3395FF]/5 transition-all"
          >
            Command Center
          </button>
          <button
            onClick={() => navigate('/checkout')}
            className="px-4 py-2 text-[13px] font-semibold text-white bg-gradient-to-r from-[#3395FF] to-[#2563eb] rounded-lg hover:shadow-lg hover:shadow-[#3395FF]/25 transition-all"
          >
            Try Demo
          </button>
        </div>

        <button className="md:hidden text-white" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:hidden bg-[#080a14]/95 backdrop-blur-xl border-b border-white/[0.06] px-6 py-4 space-y-3"
        >
          {navLinks.map((item) => (
            <button
              key={item.label}
              onClick={() => handleNav(item)}
              className="block w-full text-left text-sm text-[#94a3b8] hover:text-white py-2"
            >
              {item.label}
            </button>
          ))}
        </motion.div>
      )}
    </motion.nav>
  )
}
