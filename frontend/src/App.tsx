import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'react-hot-toast'
import Landing from './pages/Landing'
import Checkout from './pages/Checkout'
import Dashboard from './pages/Dashboard'
import TransactionDetail from './pages/TransactionDetail'
import Queue from './pages/Queue'
import Learning from './pages/Learning'
import Performance from './pages/Performance'
import Config from './pages/Config'
import Audit from './pages/Audit'
import ShadowMode from './pages/ShadowMode' // ← NEW
import DemoStore from './pages/DemoStore'

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Landing />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="/command" element={<Dashboard />} />
        <Route path="/shadow" element={<ShadowMode />} /> {/* ← NEW */}
        <Route path="/transaction/:id" element={<TransactionDetail />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/learning" element={<Learning />} />
        <Route path="/performance" element={<Performance />} />
        <Route path="/config" element={<Config />} />
        <Route path="/audit" element={<Audit />} />
      </Routes>
    </AnimatePresence>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen text-[#f0f2f5] font-sans selection:bg-[#3395FF]/30">
        <div className="orb-1" />
        <div className="orb-2" />
        <div className="orb-3" />
        <div className="grid-bg" />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#080a14',
              color: '#f0f2f5',
              border: '1px solid rgba(255,255,255,0.06)',
              fontSize: '12px',
              borderRadius: '8px',
            },
          }}
        />
        <AnimatedRoutes />
      </div>
    </BrowserRouter>
  )
}

export default App