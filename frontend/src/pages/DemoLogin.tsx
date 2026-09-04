import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Shield, Sparkles, User } from 'lucide-react'

const ACCOUNTS = [
  {
    id: 'demo.user',
    title: 'Free user',
    blurb: 'Horizon Web Studio · 40-lead free plan walkthrough',
    icon: User,
  },
  {
    id: 'demo.pro',
    title: 'Pro user',
    blurb: 'Delta Digital Agency · paid features + higher quota',
    icon: Sparkles,
  },
  {
    id: 'demo.admin',
    title: 'Platform admin',
    blurb: 'Cross-tenant demo admin dashboard',
    icon: Shield,
  },
]

export default function DemoLogin() {
  const navigate = useNavigate()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [demoOn, setDemoOn] = useState(true)

  useEffect(() => {
    fetch('/api/v1/demo/status')
      .then((r) => r.json())
      .then((d) => setDemoOn(Boolean(d.demo_mode)))
      .catch(() => setDemoOn(true))
  }, [])

  const login = async (account: string) => {
    setError('')
    setBusy(account)
    try {
      const res = await fetch('/api/v1/demo/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail?.error?.message || 'Login failed')
      }
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('demo_mode', '1')
      localStorage.setItem('demo_account', account)
      localStorage.setItem('onboarding_done', '1')
      if (account === 'demo.admin') {
        navigate('/app/admin')
      } else {
        navigate('/app')
      }
      window.location.reload()
    } catch (e: unknown) {
      setError((e as Error).message || 'Demo login failed')
      setBusy(null)
    }
  }

  if (!demoOn) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-slate-100">
        <div className="bg-white border rounded-xl p-6 max-w-md text-center">
          <p className="font-semibold">Demo mode is off on this server.</p>
          <Link to="/login" className="text-brand-600 text-sm mt-3 inline-block">
            Normal sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <p className="inline-flex text-xs font-semibold uppercase tracking-wide text-amber-300 bg-amber-500/10 border border-amber-500/30 px-3 py-1 rounded-full">
              Demo Mode · Demo Data · Simulated integrations
            </p>
            <h1 className="text-3xl font-bold mt-4 text-white">Buyer demo login</h1>
            <p className="text-slate-400 text-sm mt-2">
              No API keys required. Google Maps, Facebook, Stripe, and AI providers are{' '}
              <strong className="text-slate-200">not contacted</strong> — all flows use local
              mock adapters and realistic Bangladesh fixtures.
            </p>
          </div>

          {error && (
            <div className="mb-4 text-sm text-red-200 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="space-y-3">
            {ACCOUNTS.map((a) => (
              <button
                key={a.id}
                type="button"
                disabled={!!busy}
                onClick={() => login(a.id)}
                className="w-full text-left rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 p-4 transition flex items-start gap-3"
              >
                <div className="w-10 h-10 rounded-xl bg-brand-500/20 text-brand-300 flex items-center justify-center">
                  <a.icon size={20} />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-white">{a.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{a.blurb}</p>
                  <p className="text-[11px] font-mono text-slate-500 mt-1">{a.id}</p>
                </div>
                {busy === a.id ? (
                  <Loader2 className="animate-spin text-brand-400" size={18} />
                ) : null}
              </button>
            ))}
          </div>

          <p className="text-center text-xs text-slate-500 mt-6">
            <Link to="/login" className="underline hover:text-slate-300">
              Password login
            </Link>
            {' · '}
            <Link to="/" className="underline hover:text-slate-300">
              Marketing site
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
