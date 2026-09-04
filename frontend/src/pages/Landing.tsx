import { Link } from 'react-router-dom'
import {
  ArrowRight,
  ShieldCheck,
  Target,
  Mail,
  BarChart3,
  Sparkles,
  Check,
} from 'lucide-react'

const features = [
  {
    icon: Target,
    title: 'Opportunity, not just listings',
    body: 'Score businesses by missing websites, weak mobile, or no booking — not map popularity.',
  },
  {
    icon: Mail,
    title: 'Safe outreach',
    body: 'Human approval, suppression list, and SPF/DKIM before any send. Built for agencies who care about domain reputation.',
  },
  {
    icon: BarChart3,
    title: 'Proof metrics',
    body: 'Phone coverage, contact rates, reply rates on your own data — sell outcomes, not feature theater.',
  },
  {
    icon: ShieldCheck,
    title: 'Free to start',
    body: '40 leads / month on free plan. Template drafts included. Upgrade when you need AI personalization and higher volume.',
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="font-bold text-lg tracking-tight">
            LocalOpp<span className="text-brand-400">Finder</span>
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            <Link to="/pricing" className="text-slate-300 hover:text-white">
              Pricing
            </Link>
            <Link to="/tools/website-check" className="text-slate-300 hover:text-white">
              Free tool
            </Link>
            <Link to="/login" className="text-slate-300 hover:text-white">
              Sign in
            </Link>
            <Link
              to="/register"
              className="bg-brand-500 hover:bg-brand-400 text-white px-3 py-1.5 rounded-lg font-medium"
            >
              Start free
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="max-w-5xl mx-auto px-4 pt-16 pb-12 text-center">
          <p className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-300 bg-brand-500/10 border border-brand-500/30 rounded-full px-3 py-1 mb-6">
            <Sparkles size={12} />
            For web agencies & freelancers
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white max-w-3xl mx-auto leading-tight">
            Find local businesses that need a website or booking system
          </h1>
          <p className="mt-5 text-lg text-slate-400 max-w-2xl mx-auto">
            Not another map export. Discover under-digitized businesses, score the
            opportunity, draft outreach, and send only after you approve — with
            domain trust enforced.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 bg-white text-slate-900 hover:bg-slate-100 px-5 py-3 rounded-xl font-semibold"
            >
              <Sparkles size={18} className="text-brand-600" />
              Try interactive demo
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 bg-brand-500 hover:bg-brand-400 text-white px-5 py-3 rounded-xl font-semibold"
            >
              Create free account
              <ArrowRight size={18} />
            </Link>
            <Link
              to="/tools/website-check"
              className="inline-flex items-center gap-2 border border-white/20 hover:bg-white/5 px-5 py-3 rounded-xl font-medium"
            >
              Free website opportunity check
            </Link>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            No card required · 40 leads / month free · Invite friends for bonus leads
          </p>
        </section>

        <section className="max-w-4xl mx-auto px-4 pb-10">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-6 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
            {[
              { value: '40+', label: 'businesses scored per run' },
              { value: '4', label: 'data-gap signals scored' },
              { value: '100%', label: 'human-approved sends' },
              { value: '2', label: 'clicks to a drafted email' },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-2xl sm:text-3xl font-bold text-white">{s.value}</p>
                <p className="text-xs text-slate-400 mt-1 leading-snug">{s.label}</p>
              </div>
            ))}
          </div>
          <p className="text-center text-[11px] text-slate-600 mt-2">
            See it live — <Link to="/demo" className="underline hover:text-slate-400">open the interactive demo</Link>, no signup needed.
          </p>
        </section>

        <section className="max-w-5xl mx-auto px-4 py-12 grid sm:grid-cols-2 gap-4">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-5 text-left"
            >
              <f.icon className="text-brand-400 mb-3" size={22} />
              <h2 className="font-semibold text-white">{f.title}</h2>
              <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">{f.body}</p>
            </div>
          ))}
        </section>

        <section className="max-w-5xl mx-auto px-4 py-12">
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-brand-600/20 to-slate-900 p-8 text-center">
            <h2 className="text-2xl font-bold text-white">How teams use it</h2>
            <ol className="mt-6 grid sm:grid-cols-3 gap-4 text-left text-sm">
              {[
                'Pick a city + vertical (e.g. restaurants in Dhaka)',
                'Review scored leads — phone, site gaps, source',
                'Approve messages; we block send until DNS trust passes',
              ].map((step, i) => (
                <li
                  key={step}
                  className="rounded-xl bg-black/30 border border-white/10 p-4"
                >
                  <span className="text-brand-400 font-bold">0{i + 1}</span>
                  <p className="mt-2 text-slate-300">{step}</p>
                </li>
              ))}
            </ol>
            <Link
              to="/register"
              className="inline-flex mt-8 items-center gap-2 bg-white text-slate-900 px-5 py-3 rounded-xl font-semibold hover:bg-slate-100"
            >
              Start finding opportunities
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>

        <section className="max-w-3xl mx-auto px-4 py-10">
          <h2 className="text-center font-semibold text-white mb-4">
            Why not just Google Maps + ChatGPT?
          </h2>
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              'Maps optimizes for consumers finding businesses — not agencies finding weak online presence',
              'Generic AI writes email; it does not enforce approval, suppression, or SPF/DKIM',
              'We measure phone coverage and replies on your book of leads',
            ].map((line) => (
              <li key={line} className="flex gap-2">
                <Check className="text-brand-400 shrink-0 mt-0.5" size={16} />
                {line}
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="border-t border-white/10 mt-8">
        <div className="max-w-5xl mx-auto px-4 py-6 flex flex-wrap gap-4 justify-between text-xs text-slate-500">
          <span>© {new Date().getFullYear()} LocalOpp Finder</span>
          <div className="flex gap-4">
            <Link to="/legal/terms">Terms</Link>
            <Link to="/legal/privacy">Privacy</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="/login">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
