import { useEffect, useState } from 'react'
import { Copy, Gift, Users, Check } from 'lucide-react'
import { api } from '../lib/api'
import { PageHeader, ErrorBanner, PageSkeleton } from '../components/ui'
import { QuotaBar } from '../components/QuotaBar'

type ReferralData = {
  code: string
  share_url: string
  signup_count: number
  successful_paid_referrals: number
  bonus_leads: number
  rewards: {
    signup_inviter_leads: number
    signup_invitee_leads: number
    paid_inviter_leads: number
  }
  history: Array<{
    status: string
    inviter_reward_leads: number
    invitee_reward_leads: number
    paid_reward_granted: boolean
    created_at?: string | null
  }>
}

export default function Referrals() {
  const [data, setData] = useState<ReferralData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api
      .getReferralMe()
      .then(setData)
      .catch((e: Error) => setError(e.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Could not copy')
    }
  }

  if (loading) return <PageSkeleton />

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title="Invite & Rewards"
        description="Share your code. Friends get bonus leads; you earn more when they sign up — and again when they upgrade."
      />

      <QuotaBar />

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError('')} />
      )}

      {data && (
        <>
          <div className="bg-gradient-to-br from-brand-600 to-brand-900 text-white rounded-2xl p-6 shadow-lg">
            <div className="flex items-center gap-2 text-brand-100 text-sm mb-2">
              <Gift size={16} />
              Your invite code
            </div>
            <p className="text-3xl font-bold tracking-widest font-mono">
              {data.code}
            </p>
            <p className="text-sm text-brand-100 mt-3 break-all">
              {data.share_url}
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              <button
                type="button"
                onClick={() => copy(data.share_url)}
                className="inline-flex items-center gap-2 bg-white text-brand-800 px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-50"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? 'Copied' : 'Copy invite link'}
              </button>
              <button
                type="button"
                onClick={() => copy(data.code)}
                className="inline-flex items-center gap-2 bg-white/10 border border-white/30 px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/20"
              >
                Copy code
              </button>
            </div>
          </div>

          <div className="grid sm:grid-cols-3 gap-3">
            <div className="bg-white border rounded-xl p-4">
              <p className="text-xs text-slate-500">Signups</p>
              <p className="text-2xl font-bold">{data.signup_count}</p>
            </div>
            <div className="bg-white border rounded-xl p-4">
              <p className="text-xs text-slate-500">Paid referrals</p>
              <p className="text-2xl font-bold">
                {data.successful_paid_referrals}
              </p>
            </div>
            <div className="bg-white border rounded-xl p-4">
              <p className="text-xs text-slate-500">Bonus leads earned</p>
              <p className="text-2xl font-bold text-brand-700">
                {data.bonus_leads}
              </p>
            </div>
          </div>

          <div className="bg-white border rounded-xl p-5 space-y-3">
            <h2 className="font-semibold text-slate-900 flex items-center gap-2">
              <Users size={16} /> How rewards work
            </h2>
            <ul className="text-sm text-slate-600 space-y-2 list-disc pl-5">
              <li>
                Friend signs up with your code → they get{' '}
                <strong>{data.rewards.signup_invitee_leads}</strong> bonus
                leads; you get{' '}
                <strong>{data.rewards.signup_inviter_leads}</strong>.
              </li>
              <li>
                Friend upgrades to a paid plan → you get{' '}
                <strong>{data.rewards.paid_inviter_leads}</strong> more bonus
                leads (once).
              </li>
              <li>
                Bonus leads stack on top of Free (40) or paid plan quotas —
                enforced on the server.
              </li>
            </ul>
          </div>

          {data.history?.length > 0 && (
            <div className="bg-white border rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b font-medium text-sm">
                Recent invites
              </div>
              <ul className="divide-y">
                {data.history.map((h, i) => (
                  <li
                    key={i}
                    className="px-4 py-3 text-sm flex justify-between gap-2"
                  >
                    <span className="capitalize text-slate-700">{h.status}</span>
                    <span className="text-slate-500">
                      +{h.inviter_reward_leads} leads
                      {h.paid_reward_granted ? ' · paid bonus' : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
