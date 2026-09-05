import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { ErrorBanner, NoticeBanner, PageSkeleton } from '../components/ui'

type Sub = {
  plan_id: string
  status: string
  trial_end?: string
  current_period_end?: string
  caps: Record<string, number>
}

type Plan = {
  id: 'starter' | 'pro'
  name: string
  description: string
  price: string
  features: string[]
}

const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    description: 'For small outreach campaigns and early-stage teams.',
    price: '$29/mo',
    features: ['Campaign discovery', 'Lead qualification', 'AI message drafting', 'Human approval workflow', 'Basic pipeline'],
  },
  {
    id: 'pro',
    name: 'Pro',
    description: 'For teams running larger outbound campaigns.',
    price: '$79/mo',
    features: ['Everything in Starter', 'Higher campaign limits', 'Higher lead limits', 'Team collaboration', 'Advanced outreach workflow'],
  },
]

function formatDate(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatDateTime(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function formatStatus(status: string) {
  return status.replace(/_/g, ' ')
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const classes = normalized === 'active'
    ? 'bg-green-100 text-green-700'
    : normalized === 'trialing'
      ? 'bg-blue-100 text-blue-700'
      : normalized === 'past_due'
        ? 'bg-red-100 text-red-700'
        : 'bg-slate-100 text-slate-600'
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium capitalize ${classes}`}>{formatStatus(status)}</span>
}

function UsageBar({ label, used, limit, windowLabel, resetAt }: { label: string; used: number; limit: number; windowLabel?: string; resetAt?: string | null }) {
  const safeUsed = Math.max(0, used || 0)
  const safeLimit = Math.max(0, limit || 0)
  const percentage = safeLimit > 0 ? Math.min(100, Math.round((safeUsed / safeLimit) * 100)) : 0
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1.5">
        <span className="text-slate-600">{label}{windowLabel ? ` · ${windowLabel}` : ''}</span>
        <span className="text-slate-500">{safeUsed.toLocaleString()} / {safeLimit > 0 ? safeLimit.toLocaleString() : 'Unlimited'}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full bg-brand-600 rounded-full transition-all" style={{ width: `${percentage}%` }} />
      </div>
      {safeLimit > 0 && percentage >= 90 && (
        <p className="text-xs text-amber-600 mt-1">
          {resetAt ? `Quota resets around ${formatDateTime(resetAt)}.` : 'You are close to your limit.'}
        </p>
      )}
    </div>
  )
}

export default function Billing() {
  const [sub, setSub] = useState<Sub | null>(null)
  const [usage, setUsage] = useState<any>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [upgrading, setUpgrading] = useState<'starter' | 'pro' | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('success') === '1') setNotice('Payment completed. Your subscription will update after Stripe confirms the payment.')
    if (params.get('cancelled') === '1') setNotice('Checkout was cancelled. No payment was made.')

    const load = async () => {
      try {
        const [subscription, usageData] = await Promise.all([api.getSubscription(), api.getUsage().catch(() => null)])
        setSub(subscription)
        setUsage(usageData)
      } catch (e: unknown) {
        setError((e as Error).message || 'Failed to load billing information')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const upgrade = async (plan: 'starter' | 'pro') => {
    if (sub?.plan_id === plan) return
    setError('')
    setNotice('')
    setUpgrading(plan)
    try {
      const res = await api.subscribe(plan, { success_url: window.location.origin + '/billing?success=1', cancel_url: window.location.origin + '/billing?cancelled=1' })
      if (!res.checkout_url) throw new Error('Checkout URL was not returned by the server.')
      window.location.href = res.checkout_url
    } catch (e: unknown) {
      setError((e as Error).message || 'Checkout failed')
      setUpgrading(null)
    }
  }

  if (loading) return <PageSkeleton rows={3} />

  const caps = sub?.caps || {}
  const campaignsUsed = usage?.campaigns_used ?? usage?.campaigns ?? usage?.usage?.campaigns ?? usage?.current?.campaigns ?? 0
  const leadsUsed = usage?.leads_used ?? usage?.leads ?? usage?.usage?.leads ?? usage?.current?.leads ?? 0
  const campaignLimit = caps.max_campaigns_per_month ?? caps.max_campaigns ?? 0
  const leadLimit = usage?.leads_limit ?? caps.max_leads_per_month ?? caps.max_leads ?? 0
  const leadWindow = usage?.leads_quota_window === 'rolling_24h' ? 'rolling 24h' : 'monthly'
  const quotaReset = usage?.quota_resets_at ?? null
  const currentPlan = sub?.plan_id?.toLowerCase()

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Plan & Billing</h1>
        <p className="text-sm text-slate-500 mt-1">Manage your subscription, usage and plan limits.</p>
      </div>
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      {notice && <NoticeBanner message={notice} variant="info" onDismiss={() => setNotice('')} />}

      {sub && <>
        <section className="bg-white border rounded-xl p-5 mb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Current plan</p>
              <div className="flex items-center gap-3"><h2 className="text-xl font-bold capitalize">{sub.plan_id}</h2><StatusBadge status={sub.status} /></div>
            </div>
            {sub.current_period_end && <div className="text-sm text-right"><p className="text-xs text-slate-500">Current period ends</p><p className="font-medium">{formatDate(sub.current_period_end)}</p></div>}
          </div>
          {sub.trial_end && <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700"><strong>Trial:</strong> Your trial ends on {formatDate(sub.trial_end)}.</div>}
        </section>

        <section className="bg-white border rounded-xl p-5 mb-8">
          <div className="mb-4">
            <h2 className="font-semibold">Usage & quota</h2>
            <p className="text-xs text-slate-500 mt-1">
              {leadWindow === 'rolling 24h' ? 'Trial leads use a rolling 24-hour quota. Older leads automatically leave the window.' : 'Paid-plan lead usage follows the monthly billing period.'}
            </p>
          </div>
          <div className="space-y-5">
            <UsageBar label="Campaigns" used={campaignsUsed} limit={campaignLimit} windowLabel="monthly" />
            <UsageBar label="Leads" used={leadsUsed} limit={leadLimit} windowLabel={leadWindow} resetAt={quotaReset} />
          </div>
          {usage?.leads_remaining !== undefined && <p className="mt-4 text-sm text-slate-600"><strong>{usage.leads_remaining.toLocaleString()}</strong> leads remaining in the current quota window.</p>}
        </section>
      </>}

      <div className="flex items-center justify-between mb-3"><div><h2 className="text-lg font-semibold">Available plans</h2><p className="text-sm text-slate-500">Choose the plan that fits your outreach volume.</p></div></div>
      <div className="grid md:grid-cols-2 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = currentPlan === plan.id
          const isUpgrading = upgrading === plan.id
          return <div key={plan.id} className={`bg-white border rounded-xl p-5 relative ${isCurrent ? 'border-brand-500 ring-1 ring-brand-500' : ''}`}>
            {isCurrent && <span className="absolute top-4 right-4 text-xs font-medium bg-brand-100 text-brand-700 px-2 py-1 rounded-full">Current plan</span>}
            <h3 className="text-lg font-semibold">{plan.name}</h3><p className="text-2xl font-bold mt-2">{plan.price}</p><p className="text-sm text-slate-500 mt-2 mb-5">{plan.description}</p>
            <ul className="space-y-2 mb-6">{plan.features.map((feature) => <li key={feature} className="flex items-start gap-2 text-sm text-slate-700"><span className="text-green-600 font-bold">✓</span><span>{feature}</span></li>)}</ul>
            <button type="button" disabled={isCurrent || upgrading !== null} onClick={() => upgrade(plan.id)} className={`w-full px-4 py-2.5 rounded-lg text-sm font-medium transition ${isCurrent ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : plan.id === 'starter' ? 'bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50' : 'border border-brand-600 text-brand-700 hover:bg-brand-50 disabled:opacity-50'}`}>
              {isCurrent ? 'Current Plan' : isUpgrading ? 'Opening checkout…' : `Choose ${plan.name}`}
            </button>
          </div>
        })}
      </div>
      <div className="mt-6 p-4 bg-slate-50 border rounded-xl"><p className="text-xs text-slate-600 leading-relaxed">Payments are securely processed through Stripe. Your plan is updated after the payment webhook is successfully received by the server. If your plan does not update immediately after payment, refresh this page after a few moments.</p></div>
    </div>
  )
}
