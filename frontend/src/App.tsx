import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import RiskCommandCenter from './pages/RiskCommandCenter'
import TransactionDeepDive from './pages/TransactionDeepDive'
import QueueOracle from './pages/QueueOracle'
import OverrideLearning from './pages/OverrideLearning'
import PerformanceDashboard from './pages/PerformanceDashboard'
import Configuration from './pages/Configuration'
import SystemAudit from './pages/SystemAudit'
import { App as CheckoutApp } from './AppCheckout'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans">
        <Navbar />
        <Routes>
          <Route path="/" element={<CheckoutApp />} />
          <Route path="/command" element={<RiskCommandCenter />} />
          <Route path="/transaction/:id" element={<TransactionDeepDive />} />
          <Route path="/queue" element={<QueueOracle />} />
          <Route path="/performance" element={<PerformanceDashboard />} />
          <Route path="/learning" element={<OverrideLearning />} />
          <Route path="/config" element={<Configuration />} />
          <Route path="/audit" element={<SystemAudit />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App