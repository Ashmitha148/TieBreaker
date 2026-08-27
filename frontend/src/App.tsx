import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import RiskCommandCenter from './pages/RiskCommandCenter'
import TransactionDeepDive from './pages/TransactionDeepDive'
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
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App