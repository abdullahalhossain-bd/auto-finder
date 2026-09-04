import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, LayoutGrid, FileBarChart, X, ArrowRight } from 'lucide-react'

const STORAGE_KEY = 'welcome_tour_dismissed'

const STEPS = [
  {
    icon: Sparkles,
    title: '1. Generate leads',
    body: 'Pick an industry + city and watch discovery run step by step.',
    to: '/leads/generate',
    cta: 'Generate leads',
  },
  {
    icon: LayoutGrid,
    title: '2. Work the pipeline',
    body: 'Drag leads through stages — Contacted, Replied, Won.',
    to: '/pipeline',
    cta: 'Open pipeline',
  },
  {
    icon: FileBarChart,
    title: '3. Prove the results',
    body: 'A provenance-backed report you can put in a client deck.',
    to: '/lead-quality',
    cta: 'View report',
  },
]

export function WelcomeTour() {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(STORAGE_KEY) === '1',
  )

  if (dismissed) return null

  const close = () => {
    localStorage.setItem(STORAGE_KEY, '1')
    setDismissed(true)
  }

  return (
    <div className="relative rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-5 sm:p-6">
      <button
        type="button"
        onClick={close}
        aria-label="Dismiss"
        className="absolute top-3 right-3 text-slate-400 hover:text-slate-600 p-1"
      >
        <X size={16} />
      </button>
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700 mb-1">
        Quick start
      </p>
      <h2 className="font-bold text-slate-900 mb-4">
        Three steps to your first outreach send
      </h2>
      <div className="grid sm:grid-cols-3 gap-3">
        {STEPS.map((s) => (
          <Link
            key={s.title}
            to={s.to}
            onClick={close}
            className="group bg-white border border-slate-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-sm transition"
          >
            <s.icon size={18} className="text-brand-600 mb-2" />
            <p className="text-sm font-semibold text-slate-900">{s.title}</p>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{s.body}</p>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-brand-600 group-hover:gap-1.5 transition-all">
              {s.cta}
              <ArrowRight size={12} />
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
