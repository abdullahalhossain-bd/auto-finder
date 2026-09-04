import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export type QuotaSnapshot = {
  plan: string
  is_paid?: boolean
  leads_used: number
  leads_limit: number
  leads_remaining: number
  percent_used: number
  features?: Record<string, boolean>
}

export function useQuota(pollMs = 30000) {
  const [quota, setQuota] = useState<QuotaSnapshot | null>(null)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const data = await api.getUsage()
      const used = data.leads_used ?? data.usage?.leads ?? 0
      const limit =
        data.leads_limit ?? data.caps?.max_leads_per_month ?? 40
      const remaining =
        data.leads_remaining ?? Math.max(0, limit - used)
      const percent =
        data.percent_used ??
        (limit ? Math.round((used / limit) * 1000) / 10 : 0)
      setQuota({
        plan: data.plan || 'free',
        is_paid: Boolean(data.is_paid),
        leads_used: used,
        leads_limit: limit,
        leads_remaining: remaining,
        percent_used: percent,
        features: data.features,
      })
      setError('')
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to load quota')
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, pollMs)
    return () => clearInterval(t)
  }, [pollMs])

  return { quota, error, reload: load }
}

/** Compact always-visible quota (header / sidebar). Quota ≠ generation progress. */
export function QuotaBar({ compact = false }: { compact?: boolean }) {
  const { quota } = useQuota()
  if (!quota) {
    return (
      <div className="text-xs text-slate-400 animate-pulse">
        Loading quota…
      </div>
    )
  }

  const { leads_used, leads_limit, leads_remaining, percent_used, is_paid, plan } =
    quota
  const warn = percent_used >= 80
  const full = leads_remaining <= 0

  return (
    <div
      className={
        compact
          ? 'space-y-1'
          : 'bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm'
      }
      aria-label="Lead quota usage"
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-medium text-slate-700">
          {leads_used.toLocaleString()} / {leads_limit.toLocaleString()} Leads
          Used
        </span>
        <span
          className={`font-semibold ${
            full ? 'text-red-600' : warn ? 'text-amber-600' : 'text-slate-500'
          }`}
        >
          {percent_used}% Used
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            full ? 'bg-red-500' : warn ? 'bg-amber-500' : 'bg-brand-600'
          }`}
          style={{ width: `${Math.min(100, percent_used)}%` }}
        />
      </div>
      <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500">
        <span>{leads_remaining.toLocaleString()} Remaining</span>
        <span className="capitalize">
          {plan}
          {!is_paid && (
            <Link
              to="/billing"
              className="ml-2 text-brand-600 font-medium hover:underline"
            >
              Upgrade
            </Link>
          )}
        </span>
      </div>
    </div>
  )
}

export function PaidLock({
  feature,
  title,
  description,
}: {
  feature?: string
  title: string
  description?: string
}) {
  return (
    <div className="relative rounded-2xl border border-slate-200 bg-slate-50 overflow-hidden">
      <div className="absolute inset-0 bg-white/70 backdrop-blur-[1px] z-10 flex flex-col items-center justify-center p-6 text-center">
        <span className="text-xs font-semibold uppercase tracking-wide text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded-full mb-3">
          Paid feature
        </span>
        <h3 className="text-base font-semibold text-slate-900">{title}</h3>
        {description && (
          <p className="text-sm text-slate-500 mt-1 max-w-sm">{description}</p>
        )}
        {feature && (
          <p className="text-[11px] text-slate-400 mt-1 font-mono">{feature}</p>
        )}
        <Link
          to="/billing"
          className="mt-4 inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700"
        >
          Upgrade to unlock
        </Link>
      </div>
      <div className="p-8 opacity-40 pointer-events-none select-none" aria-hidden>
        <div className="h-8 w-48 bg-slate-200 rounded mb-4" />
        <div className="h-24 bg-slate-100 rounded-xl" />
      </div>
    </div>
  )
}
