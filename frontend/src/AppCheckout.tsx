import React, { useState, useEffect, useCallback } from 'react'

interface ServerConfig {
  is_configured: boolean
  environment: string
  is_test_mode: boolean
  razorpay_key_id: string | null
}

interface PaymentRecord {
  id: number
  razorpay_payment_id: string
  razorpay_order_id: string | null
  order_id: number | null
  amount: number
  currency: string
  status: string
  method: string | null
  bank: string | null
  wallet: string | null
  vpa: string | null
  email: string | null
  contact: string | null
  error_code: string | null
  error_description: string | null
  created_at: string
}

interface RazorpaySuccessResponse {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

interface RazorpayFailureResponse {
  error: {
    code: string
    description: string
    source: string
    step: string
    reason: string
    metadata: {
      order_id?: string
      payment_id?: string
    }
  }
}

declare global {
  interface Window {
    Razorpay: any
  }
}

export const App: React.FC = () => {
  const [config, setConfig] = useState<ServerConfig | null>(null)
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [loadingPayments, setLoadingPayments] = useState(false)
  const [paying, setPaying] = useState(false)
  
  // Checkout form state
  const [amountInr, setAmountInr] = useState<number>(500)
  const [customerEmail, setCustomerEmail] = useState<string>('demo.customer@example.com')
  const [customerPhone, setCustomerPhone] = useState<string>('9999999999')
  
  // Status banner state
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error' | 'info'
    title: string
    detail: string
  } | null>(null)

  const apiBase = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

  // Fetch public config
  const fetchConfig = useCallback(async () => {
    try {
      setLoadingConfig(true)
      const res = await fetch(`${apiBase}/api/config`)
      if (res.ok) {
        const data = await res.json()
        setConfig(data)
      }
    } catch (err) {
      console.error('Failed to fetch config', err)
    } finally {
      setLoadingConfig(false)
    }
  }, [apiBase])

  // Fetch payments list
  const fetchPayments = useCallback(async () => {
    try {
      setLoadingPayments(true)
      const res = await fetch(`${apiBase}/api/payments`)
      if (res.ok) {
        const data = await res.json()
        setPayments(data)
      }
    } catch (err) {
      console.error('Failed to fetch payments', err)
    } finally {
      setLoadingPayments(false)
    }
  }, [apiBase])

  useEffect(() => {
    fetchConfig()
    fetchPayments()

    // Poll payments periodically every 5 seconds to capture asynchronous webhook updates
    const interval = setInterval(fetchPayments, 5000)
    return () => clearInterval(interval)
  }, [fetchConfig, fetchPayments])

  // Load Razorpay Checkout.js script dynamically
  const loadRazorpayScript = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true)
        return
      }
      const script = document.createElement('script')
      script.src = 'https://checkout.razorpay.com/v1/checkout.js'
      script.onload = () => resolve(true)
      script.onerror = () => resolve(false)
      document.body.appendChild(script)
    })
  }

  // Handle Checkout initiation
  const handlePayNow = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatusMessage(null)

    if (!config?.is_configured) {
      setStatusMessage({
        type: 'error',
        title: 'Razorpay Not Configured',
        detail: 'Please configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in the backend .env file.',
      })
      return
    }

    setPaying(true)

    try {
      const scriptLoaded = await loadRazorpayScript()
      if (!scriptLoaded) {
        throw new Error('Failed to load Razorpay Checkout script. Check internet connectivity.')
      }

      // 1. Create order on backend
      const amountPaise = Math.round(amountInr * 100)
      const orderRes = await fetch(`${apiBase}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: amountPaise,
          currency: 'INR',
          receipt: `demo_${Date.now()}`,
          notes: {
            customer_email: customerEmail,
            demo_store: 'TieBreaker Phase 1',
          },
        }),
      })

      if (!orderRes.ok) {
        const errorData = await orderRes.json().catch(() => ({}))
        throw new Error(errorData.detail || `Order creation failed (HTTP ${orderRes.status})`)
      }

      const orderData = await orderRes.json()

      // 2. Open Razorpay Checkout modal
      const options = {
        key: orderData.key_id || config.razorpay_key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'TieBreaker Demo Store',
        description: 'Payment Flow Verification (Test Mode)',
        order_id: orderData.razorpay_order_id,
        prefill: {
          email: customerEmail,
          contact: customerPhone,
        },
        theme: {
          color: '#3b82f6',
        },
        modal: {
          ondismiss: () => {
            setPaying(false)
          },
        },
        handler: async (response: RazorpaySuccessResponse) => {
          setPaying(false)
          setStatusMessage({
            type: 'success',
            title: 'Payment Successful',
            detail: `Payment ID: ${response.razorpay_payment_id} | Order ID: ${response.razorpay_order_id}. Webhook will process status asynchronously.`,
          })
          // Immediately refresh payment list
          fetchPayments()
        },
      }

      const rzp = new window.Razorpay(options)
      rzp.on('payment.failed', (response: RazorpayFailureResponse) => {
        setPaying(false)
        setStatusMessage({
          type: 'error',
          title: 'Payment Failed',
          detail: `Reason: ${response.error?.description || response.error?.reason || 'Payment failed in test mode'}. (Code: ${response.error?.code})`,
        })
        fetchPayments()
      })

      rzp.open()
    } catch (err: any) {
      setPaying(false)
      setStatusMessage({
        type: 'error',
        title: 'Checkout Error',
        detail: err.message || 'An unexpected error occurred.',
      })
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center">
      {/* Mandatory Test Mode Banner */}
      <header className="w-full bg-amber-500/10 border-b border-amber-500/30 px-4 py-2.5 text-center text-xs md:text-sm font-semibold text-amber-300 tracking-wider">
        ⚠️ TIEBREAKER DEMO STORE — RAZORPAY TEST MODE — NO REAL MONEY — TEST / DEMO ENVIRONMENT
      </header>

      <main className="max-w-5xl w-full p-4 md:p-8 space-y-8">
        {/* Header Title */}
        <section className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-black tracking-tight text-white">TieBreaker</h1>
              <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 rounded-full">
                Phase 1: Real Razorpay Test Slice
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Payment Routing &amp; Strike Decision Engine &bull; Test Mode Checkout &amp; Webhook Pipeline
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Backend Status:</span>
            {loadingConfig ? (
              <span className="text-slate-500">Checking...</span>
            ) : config?.is_configured ? (
              <span className="inline-flex items-center text-emerald-400 font-medium bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-800/40">
                <span className="w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
                Razorpay Test Mode Ready ({config.razorpay_key_id})
              </span>
            ) : (
              <span className="inline-flex items-center text-amber-400 font-medium bg-amber-950/40 px-2.5 py-1 rounded border border-amber-800/40">
                <span className="w-2 h-2 rounded-full bg-amber-400 mr-1.5"></span>
                Razorpay Unconfigured (.env missing keys)
              </span>
            )}
          </div>
        </section>

        {/* Status Message Alert */}
        {statusMessage && (
          <div
            className={`p-4 rounded-xl border ${
              statusMessage.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200'
                : statusMessage.type === 'error'
                ? 'bg-rose-950/40 border-rose-800/60 text-rose-200'
                : 'bg-blue-950/40 border-blue-800/60 text-blue-200'
            }`}
          >
            <div className="font-semibold text-sm">{statusMessage.title}</div>
            <div className="text-xs mt-1 opacity-90">{statusMessage.detail}</div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
          {/* Checkout Column */}
          <section className="md:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white">Demo Checkout</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Simulate customer payments using Razorpay Test Mode Checkout
              </p>
            </div>

            <form onSubmit={handlePayNow} className="space-y-4">
              {/* Preset Amounts */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Select Amount (INR)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[100, 500, 1000].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setAmountInr(amt)}
                      className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                        amountInr === amt
                          ? 'bg-blue-600 border-blue-500 text-white shadow-md shadow-blue-600/20'
                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      ₹{amt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Amount */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400">Custom Amount (₹)</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={amountInr}
                  onChange={(e) => setAmountInr(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                  required
                />
              </div>

              {/* Customer Email */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400">Customer Email</label>
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                  required
                />
              </div>

              {/* Customer Phone */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400">Customer Phone</label>
                <input
                  type="tel"
                  value={customerPhone}
                  onChange={(e) => setCustomerPhone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                  required
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={paying || !config?.is_configured}
                className={`w-full py-3 px-4 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
                  !config?.is_configured
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
                    : paying
                    ? 'bg-blue-600/70 text-white cursor-wait'
                    : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30 active:scale-[0.99]'
                }`}
              >
                {paying ? (
                  <span>Opening Razorpay Checkout...</span>
                ) : !config?.is_configured ? (
                  <span>Razorpay Unconfigured</span>
                ) : (
                  <span>Pay ₹{amountInr} (Test Mode)</span>
                )}
              </button>
            </form>

            <div className="text-[11px] text-slate-500 leading-relaxed pt-2 border-t border-slate-800/80">
              Orders are created securely on the backend. When test payment is made, Razorpay sends an HMAC-verified webhook to persist the transaction asynchronously.
            </div>
          </section>

          {/* Persisted Transactions Feed Column */}
          <section className="md:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 flex flex-col">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Persisted Transactions</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Real-time database records from Razorpay webhooks &amp; checkouts
                </p>
              </div>
              <button
                onClick={fetchPayments}
                disabled={loadingPayments}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition-colors"
              >
                {loadingPayments ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>

            <div className="flex-1 overflow-x-auto">
              {payments.length === 0 ? (
                <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl">
                  <div className="text-slate-500 text-sm font-medium">No transactions recorded yet</div>
                  <div className="text-slate-600 text-xs mt-1">
                    Complete a test payment or trigger a webhook to view records here.
                  </div>
                </div>
              ) : (
                <div className="border border-slate-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                      <tr>
                        <th className="p-3">Payment ID</th>
                        <th className="p-3">Amount</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Method</th>
                        <th className="p-3">Time</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {payments.map((p) => (
                        <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="p-3 text-slate-300">
                            <div>{p.razorpay_payment_id}</div>
                            {p.razorpay_order_id && (
                              <div className="text-[10px] text-slate-500">{p.razorpay_order_id}</div>
                            )}
                          </td>
                          <td className="p-3 font-semibold text-white">
                            ₹{(p.amount / 100).toFixed(2)}
                          </td>
                          <td className="p-3 font-sans">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                                p.status === 'captured' || p.status === 'paid'
                                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                                  : p.status === 'authorized'
                                  ? 'bg-blue-950 text-blue-400 border border-blue-800/60'
                                  : p.status === 'failed'
                                  ? 'bg-rose-950 text-rose-400 border border-rose-800/60'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {p.status}
                            </span>
                            {p.error_code && (
                              <div className="text-[10px] text-rose-400 mt-1 font-mono">
                                {p.error_code}
                              </div>
                            )}
                          </td>
                          <td className="p-3 text-slate-400 uppercase font-sans text-[11px]">
                            {p.method || '—'}
                          </td>
                          <td className="p-3 text-slate-500 text-[11px] font-sans">
                            {new Date(p.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}

export default App