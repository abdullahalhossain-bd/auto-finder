import { useEffect, useRef, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  MapPin,
  Building2,
  Search,
  Sparkles,
  AlertCircle,
  Loader2,
  Check,
  MapPinned,
  Facebook,
  Layers,
  Copy,
  BrainCircuit,
  PartyPopper,
} from 'lucide-react'
import { api } from '../lib/api'
import { QuotaBar, useQuota } from '../components/QuotaBar'
import { PageHeader, ErrorBanner } from '../components/ui'

const GEN_STEPS = [
  { id: 'initializing', label: 'Initializing', icon: Loader2 },
  { id: 'google_maps', label: 'Searching Google Maps', icon: MapPinned },
  { id: 'google_search', label: 'Searching Google', icon: Search },
  { id: 'facebook', label: 'Checking Facebook', icon: Facebook },
  { id: 'collecting', label: 'Collecting businesses', icon: Layers },
  { id: 'deduping', label: 'Removing duplicates', icon: Copy },
  { id: 'scoring', label: 'AI scoring', icon: BrainCircuit },
  { id: 'completed', label: 'Completed', icon: PartyPopper },
] as const

const INDUSTRIES = [
  'Restaurant',
  'Cafe',
  'Salon / Beauty',
  'Clinic / Healthcare',
  'Gym / Fitness',
  'Retail store',
  'Hotel',
  'Auto service',
  'Real estate',
  'Other local business',
]

const COUNTRIES = ['Bangladesh', 'India', 'United States', 'United Kingdom', 'Other']

const SOURCES = [
  {
    id: 'google_places',
    label: 'Google Maps / Places',
    hint: 'Official Places API when enabled',
  },
  {
    id: 'osm',
    label: 'OpenStreetMap',
    hint: 'Default free discovery seed',
  },
  {
    id: 'google_search',
    label: 'Google Search',
    hint: 'Authorized enrichment only',
    paid: true,
  },
  {
    id: 'facebook',
    label: 'Facebook',
    hint: 'Official Graph API — coming soon',
    paid: true,
    disabled: true,
  },
]

export default function LeadGeneration() {
  const navigate = useNavigate()
  const { quota, reload } = useQuota(15000)

  const [industry, setIndustry] = useState('Restaurant')
  const [country, setCountry] = useState('Bangladesh')
  const [city, setCity] = useState('Dhaka')
  const [target, setTarget] = useState(40)
  const [sources, setSources] = useState<string[]>(['osm', 'google_places'])
  const [filters, setFilters] = useState({
    no_website: true,
    no_booking: true,
    has_phone: false,
  })

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  // Generation progress — separate from quota
  const [genStatus, setGenStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const [found, setFound] = useState(0)
  const [displayFound, setDisplayFound] = useState(0)
  const [stepIndex, setStepIndex] = useState(0)
  const stepTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const remaining = quota?.leads_remaining ?? 40
  const limit = quota?.leads_limit ?? 40
  const maxTarget = Math.min(target, Math.max(1, remaining))

  // Smoothly count the "found" number up toward its real value
  useEffect(() => {
    if (displayFound === found) return
    const step = Math.max(1, Math.ceil((found - displayFound) / 6))
    const t = setTimeout(() => {
      setDisplayFound((v) => Math.min(found, v + step))
    }, 60)
    return () => clearTimeout(t)
  }, [found, displayFound])

  // Step the visual pipeline forward while generation is running
  useEffect(() => {
    if (genStatus !== 'running') {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current)
      return
    }
    setStepIndex(0)
    stepTimerRef.current = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, GEN_STEPS.length - 2))
    }, 550)
    return () => {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current)
    }
  }, [genStatus])

  useEffect(() => {
    if (genStatus === 'done') {
      setStepIndex(GEN_STEPS.length - 1)
    }
  }, [genStatus])

  const toggleSource = (id: string, disabled?: boolean) => {
    if (disabled) return
    setSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    )
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!city.trim()) {
      setError('City / area is required')
      return
    }
    if (remaining <= 0) {
      setError(
        `Lead quota exhausted (${quota?.leads_used}/${limit}). Upgrade to generate more.`
      )
      return
    }
    if (sources.length === 0) {
      setError('Select at least one data source')
      return
    }

    const want = Math.min(Math.max(1, target), remaining)
    const nl = `Find ${want} ${industry} businesses in ${city}, ${country} that need websites or online booking`

    setSubmitting(true)
    setGenStatus('running')
    setFound(0)

    try {
      const campaign = await api.createCampaign({
        natural_language_input: nl,
        structured_params: {
          industry,
          country,
          city,
          target_leads: want,
          sources,
          filters,
        },
      })
      // Poll status for progress display (not quota)
      const id = campaign.id
      let ticks = 0
      const poll = async () => {
        ticks += 1
        try {
          const c = await api.getCampaign(id)
          const total = c.total_leads_found ?? 0
          setFound(total)
          if (
            c.status === 'completed' ||
            c.status === 'ready_for_review' ||
            c.status === 'failed' ||
            ticks > 40
          ) {
            setGenStatus('done')
            setSubmitting(false)
            reload()
            navigate(`/campaigns/${id}`)
            return
          }
          setTimeout(poll, 2000)
        } catch {
          setGenStatus('done')
          setSubmitting(false)
          navigate(`/campaigns/${id}`)
        }
      }
      setTimeout(poll, 1500)
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to start lead generation')
      setGenStatus('idle')
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title="Lead Generation"
        description="Discover local businesses with clear quota vs generation progress."
      />

      <QuotaBar />

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError('')} />
      )}

      {/* Generation progress — NOT quota */}
      {genStatus === 'running' && (
        <div
          className="rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 to-white px-5 py-5"
          role="status"
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-blue-900">
              Generating leads…
            </p>
            <p className="text-2xl font-bold text-blue-700 tabular-nums">
              {displayFound}
              <span className="text-sm text-blue-400 font-normal"> / {maxTarget}</span>
            </p>
          </div>

          <ol className="space-y-2">
            {GEN_STEPS.map((step, i) => {
              const isDone = i < stepIndex
              const isCurrent = i === stepIndex
              const Icon = step.icon
              return (
                <li
                  key={step.id}
                  className={`flex items-center gap-3 text-sm rounded-lg px-2 py-1.5 transition-colors ${
                    isCurrent ? 'bg-blue-100/70' : ''
                  }`}
                >
                  <span
                    className={`flex items-center justify-center h-6 w-6 rounded-full shrink-0 ${
                      isDone
                        ? 'bg-green-500 text-white'
                        : isCurrent
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-200 text-slate-400'
                    }`}
                  >
                    {isDone ? (
                      <Check size={13} />
                    ) : (
                      <Icon
                        size={13}
                        className={isCurrent ? 'animate-pulse' : ''}
                      />
                    )}
                  </span>
                  <span
                    className={
                      isDone
                        ? 'text-slate-500 line-through decoration-slate-300'
                        : isCurrent
                        ? 'text-blue-900 font-medium'
                        : 'text-slate-400'
                    }
                  >
                    {step.label}
                  </span>
                </li>
              )
            })}
          </ol>
          <p className="text-[11px] text-blue-400 mt-3">
            Job progress shown above — separate from your monthly lead quota.
          </p>
        </div>
      )}

      {genStatus === 'done' && found > 0 && (
        <div className="rounded-2xl border border-green-200 bg-green-50 px-5 py-4 flex items-center gap-3">
          <PartyPopper className="text-green-600 shrink-0" size={20} />
          <p className="text-sm text-green-900">
            <strong>{found} leads generated.</strong> Redirecting to the campaign…
          </p>
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 space-y-5 shadow-sm"
      >
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="block text-sm">
            <span className="font-medium text-slate-700 flex items-center gap-1.5 mb-1.5">
              <Building2 size={14} /> Industry / business type
            </span>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            >
              {INDUSTRIES.map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700 mb-1.5 block">Country</span>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-brand-500"
            >
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <label className="block text-sm">
            <span className="font-medium text-slate-700 flex items-center gap-1.5 mb-1.5">
              <MapPin size={14} /> City / area
            </span>
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g. Dhaka"
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-brand-500"
              required
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700 mb-1.5 block">
              Number of leads
            </span>
            <input
              type="number"
              min={1}
              max={remaining || 1}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value) || 1)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-brand-500"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Capped by remaining quota ({remaining} left)
            </p>
          </label>
        </div>

        <fieldset>
          <legend className="text-sm font-medium text-slate-700 mb-2">
            Lead filters
          </legend>
          <div className="flex flex-wrap gap-3">
            {(
              [
                ['no_website', 'No / weak website'],
                ['no_booking', 'No online booking'],
                ['has_phone', 'Has phone'],
              ] as const
            ).map(([key, label]) => (
              <label
                key={key}
                className="inline-flex items-center gap-2 text-sm text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={filters[key]}
                  onChange={(e) =>
                    setFilters((f) => ({ ...f, [key]: e.target.checked }))
                  }
                  className="rounded border-slate-300 text-brand-600"
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-1.5">
            <Search size={14} /> Data sources
          </legend>
          <div className="grid sm:grid-cols-2 gap-2">
            {SOURCES.map((s) => {
              const on = sources.includes(s.id)
              return (
                <button
                  key={s.id}
                  type="button"
                  disabled={s.disabled}
                  onClick={() => toggleSource(s.id, s.disabled)}
                  className={`text-left rounded-xl border px-3 py-3 transition ${
                    on
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-slate-200 hover:border-slate-300'
                  } ${s.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-slate-800">
                      {s.label}
                    </span>
                    {s.paid && (
                      <span className="text-[10px] uppercase font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
                        Paid
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">{s.hint}</p>
                </button>
              )
            })}
          </div>
        </fieldset>

        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100">
          <button
            type="submit"
            disabled={submitting || remaining <= 0}
            className="inline-flex items-center gap-2 bg-brand-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {submitting ? 'Starting…' : 'Generate leads'}
          </button>
          {remaining <= 0 && (
            <Link
              to="/billing"
              className="text-sm font-medium text-brand-600 hover:underline"
            >
              Upgrade plan
            </Link>
          )}
          <p className="text-xs text-slate-500 flex items-center gap-1">
            <AlertCircle size={12} />
            Quota usage is separate from “Leads Found” progress.
          </p>
        </div>
      </form>
    </div>
  )
}
