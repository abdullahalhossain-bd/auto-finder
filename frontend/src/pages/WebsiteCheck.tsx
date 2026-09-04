import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, ArrowRight } from 'lucide-react'

type Result = {
  headline: string
  opportunity_score: number
  tier_label?: string
  signals: Record<string, unknown>
  cta: { message: string; register_path: string }
}

export default function WebsiteCheck() {
  const [url, setUrl] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [email, setEmail] = useState('')
  const [waitMsg, setWaitMsg] = useState('')

  const onCheck = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const res = await fetch('/api/v1/public/check-website', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          business_name: name || undefined,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || 'Check failed')
      }
      setResult(data)
    } catch (err: unknown) {
      setError((err as Error).message || 'Check failed')
    } finally {
      setLoading(false)
    }
  }

  const onWaitlist = async (e: FormEvent) => {
    e.preventDefault()
    setWaitMsg('')
    try {
      const res = await fetch('/api/v1/public/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role: 'agency' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error?.message || 'Failed')
      setWaitMsg(data.message || 'Saved')
    } catch (err: unknown) {
      setWaitMsg((err as Error).message)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="max-w-xl mx-auto px-4 py-4 flex justify-between text-sm">
          <Link to="/" className="font-bold text-slate-900">
            LocalOpp Finder
          </Link>
          <Link to="/register" className="text-brand-600 font-medium">
            Start free
          </Link>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-10">
        <h1 className="text-2xl font-bold text-slate-900">
          Free website opportunity check
        </h1>
        <p className="text-sm text-slate-500 mt-2">
          Paste any business URL. We run the same class of rules used in lead scoring
          (SSL, mobile viewport, known booking vendors) — no login required.
        </p>

        <form onSubmit={onCheck} className="mt-6 space-y-3 bg-white border rounded-2xl p-5">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Website URL</span>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example-restaurant.com"
              required
              className="mt-1 w-full border rounded-lg px-3 py-2.5 text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Business name (optional)</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full border rounded-lg px-3 py-2.5 text-sm"
            />
          </label>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-brand-700 disabled:opacity-50 inline-flex justify-center items-center gap-2"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {loading ? 'Checking…' : 'Check opportunity'}
          </button>
        </form>

        {result && (
          <div className="mt-6 bg-white border rounded-2xl p-5 space-y-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Result</p>
            <p className="font-semibold text-slate-900">{result.headline}</p>
            <p className="text-3xl font-bold text-brand-700">
              {Math.round(result.opportunity_score)}
              <span className="text-sm font-medium text-slate-500 ml-2">
                / 100 · {result.tier_label || 'scored'}
              </span>
            </p>
            <ul className="text-sm text-slate-600 grid grid-cols-2 gap-2">
              <li>Reachable: {String(result.signals.reachable)}</li>
              <li>SSL: {String(result.signals.ssl)}</li>
              <li>Mobile viewport: {String(result.signals.mobile_viewport)}</li>
              <li>
                Booking vendor:{' '}
                {result.signals.booking_vendor
                  ? String(result.signals.booking_vendor)
                  : 'none detected'}
              </li>
            </ul>
            <p className="text-sm text-slate-600 border-t pt-3">{result.cta.message}</p>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-semibold"
            >
              Find more in my city
              <ArrowRight size={16} />
            </Link>
          </div>
        )}

        <div className="mt-10 border-t pt-8">
          <h2 className="font-semibold text-slate-900">Not ready to sign up?</h2>
          <p className="text-sm text-slate-500 mt-1">
            Leave your email for city playbooks and product tips.
          </p>
          <form onSubmit={onWaitlist} className="mt-3 flex gap-2">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@agency.com"
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium"
            >
              Join
            </button>
          </form>
          {waitMsg && <p className="text-xs text-slate-500 mt-2">{waitMsg}</p>}
        </div>
      </main>
    </div>
  )
}
