import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Calculator } from 'lucide-react'

const plans = [
  {
    name: 'Free',
    price: '$0',
    blurb: 'Prove the workflow on real local leads.',
    features: [
      '40 leads / month',
      'Template message drafts',
      'Human approval + suppression',
      'Opportunity score (rules-based)',
      'CSV export with provenance',
    ],
    cta: 'Start free',
    to: '/register',
    highlight: false,
  },
  {
    name: 'Starter',
    price: 'Paid',
    blurb: 'For freelancers shipping outreach weekly.',
    features: [
      '500 leads / month',
      'AI message personalization',
      'Higher campaign limits',
      'Invite rewards stack on quota',
      'Email support',
    ],
    cta: 'Create account',
    to: '/register',
    highlight: true,
  },
  {
    name: 'Pro',
    price: 'Paid',
    blurb: 'For agencies running multiple cities.',
    features: [
      '5,000 leads / month',
      'AI personalization + advanced analytics',
      'Team invites (owner controls)',
      'Priority sending caps',
      'Best for multi-client ops',
    ],
    cta: 'Create account',
    to: '/register',
    highlight: false,
  },
]

export default function Pricing() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link to="/" className="font-bold text-slate-900">
            LocalOpp Finder
          </Link>
          <div className="flex gap-3 text-sm">
            <Link to="/tools/website-check" className="text-slate-600 hover:text-slate-900">
              Free tool
            </Link>
            <Link to="/register" className="text-brand-600 font-medium">
              Start free
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold text-center text-slate-900">
          Simple pricing
        </h1>
        <p className="text-center text-slate-500 mt-2 max-w-xl mx-auto">
          Free is real product — not a demo. Upgrade when volume or AI personalization
          pays for itself.
        </p>

        <div className="mt-10 grid md:grid-cols-3 gap-5">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`rounded-2xl border bg-white p-6 flex flex-col ${
                p.highlight
                  ? 'border-brand-500 shadow-lg ring-2 ring-brand-500/20'
                  : 'border-slate-200'
              }`}
            >
              <h2 className="font-bold text-lg text-slate-900">{p.name}</h2>
              <p className="text-3xl font-bold mt-2 text-slate-900">{p.price}</p>
              <p className="text-sm text-slate-500 mt-1">{p.blurb}</p>
              <ul className="mt-5 space-y-2 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex gap-2 text-sm text-slate-700">
                    <Check size={16} className="text-brand-600 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                to={p.to}
                className={`mt-6 text-center py-2.5 rounded-lg text-sm font-semibold ${
                  p.highlight
                    ? 'bg-brand-600 text-white hover:bg-brand-700'
                    : 'border border-slate-300 hover:bg-slate-50'
                }`}
              >
                {p.cta}
              </Link>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-slate-400 mt-8">
          Referral codes grant bonus leads on top of plan caps. Billing is self-serve after
          signup.
        </p>

        <RoiCalculator />
      </main>
    </div>
  )
}

function RoiCalculator() {
  const [leads, setLeads] = useState(200)
  const [closeRate, setCloseRate] = useState(5)
  const [dealValue, setDealValue] = useState(500)

  const { deals, revenue, planCost } = useMemo(() => {
    const d = Math.round((leads * closeRate) / 100)
    const r = d * dealValue
    const cost = leads <= 40 ? 0 : leads <= 500 ? 49 : 149
    return { deals: d, revenue: r, planCost: cost }
  }, [leads, closeRate, dealValue])

  const roiMultiple = planCost > 0 ? Math.round(revenue / planCost) : null

  return (
    <div className="mt-14 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
      <div className="flex items-center gap-2 mb-1">
        <Calculator size={18} className="text-brand-600" />
        <h2 className="font-bold text-lg text-slate-900">
          Quick ROI estimate
        </h2>
      </div>
      <p className="text-sm text-slate-500 mb-6">
        Rough numbers to sanity-check the math — not a guarantee.
      </p>

      <div className="grid sm:grid-cols-3 gap-6">
        <label className="block">
          <span className="text-xs font-medium text-slate-600">
            Leads / month
          </span>
          <input
            type="range"
            min={40}
            max={5000}
            step={10}
            value={leads}
            onChange={(e) => setLeads(Number(e.target.value))}
            className="w-full mt-2 accent-brand-600"
          />
          <span className="text-sm font-semibold text-slate-900">{leads}</span>
        </label>

        <label className="block">
          <span className="text-xs font-medium text-slate-600">
            Close rate (%)
          </span>
          <input
            type="range"
            min={1}
            max={20}
            step={1}
            value={closeRate}
            onChange={(e) => setCloseRate(Number(e.target.value))}
            className="w-full mt-2 accent-brand-600"
          />
          <span className="text-sm font-semibold text-slate-900">{closeRate}%</span>
        </label>

        <label className="block">
          <span className="text-xs font-medium text-slate-600">
            Avg. deal value ($)
          </span>
          <input
            type="range"
            min={50}
            max={5000}
            step={50}
            value={dealValue}
            onChange={(e) => setDealValue(Number(e.target.value))}
            className="w-full mt-2 accent-brand-600"
          />
          <span className="text-sm font-semibold text-slate-900">${dealValue}</span>
        </label>
      </div>

      <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
        <div className="rounded-xl bg-slate-50 border p-4">
          <p className="text-xl font-bold text-slate-900">{leads}</p>
          <p className="text-xs text-slate-500 mt-1">leads / month</p>
        </div>
        <div className="rounded-xl bg-slate-50 border p-4">
          <p className="text-xl font-bold text-slate-900">{deals}</p>
          <p className="text-xs text-slate-500 mt-1">deals closed / month</p>
        </div>
        <div className="rounded-xl bg-brand-50 border border-brand-200 p-4">
          <p className="text-xl font-bold text-brand-700">
            ${revenue.toLocaleString()}
          </p>
          <p className="text-xs text-brand-600 mt-1">est. revenue / month</p>
        </div>
        <div className="rounded-xl bg-slate-50 border p-4">
          <p className="text-xl font-bold text-slate-900">
            {planCost === 0 ? 'Free' : `$${planCost}`}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {roiMultiple ? `plan pays for itself ${roiMultiple}× over` : 'plan cost'}
          </p>
        </div>
      </div>

      <Link
        to="/register"
        className="mt-6 inline-flex items-center justify-center w-full sm:w-auto bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-lg text-sm font-semibold"
      >
        Start free and test this on real leads
      </Link>
    </div>
  )
}
