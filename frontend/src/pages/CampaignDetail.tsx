import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Campaign, Lead } from '../types'
import {
  Play,
  ArrowLeft,
  RefreshCw,
  MapPin,
  Phone,
  Globe,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { PageSkeleton, CardListSkeleton, EmptyState, ErrorBanner } from '../components/ui'

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  const load = async (showRefreshing = false) => {
    if (!id) return

    if (showRefreshing) {
      setRefreshing(true)
    }

    try {
      const [c, l] = await Promise.all([
        api.getCampaign(id),
        api.listLeads(id),
      ])

      setCampaign(c)
      setLeads(l.items)
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load campaign')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  /*
   * Auto-refresh while discovery is running.
   * This allows the page to update without manually refreshing.
   */
  useEffect(() => {
    if (!campaign) return

    const activeStatuses = ['running', 'processing']

    if (!activeStatuses.includes(campaign.status)) {
      return
    }

    const interval = setInterval(() => {
      load()
    }, 5000)

    return () => clearInterval(interval)
  }, [campaign?.status, id])

  const handleStart = async () => {
    if (!id) return

    setStarting(true)
    setError('')

    try {
      await api.startCampaign(id)
      await load(true)
    } catch (e: any) {
      setError(e?.message || 'Failed to start discovery')
    } finally {
      setStarting(false)
    }
  }

  if (loading) {
    return <PageSkeleton />
  }

  if (!campaign) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-5">
        Campaign not found.
      </div>
    )
  }

  const params = campaign.structured_params as Record<string, any> | null

  const canStart =
    campaign.status === 'draft' ||
    campaign.status === 'paused' ||
    campaign.status === 'failed'

  const isRunning =
    campaign.status === 'running' ||
    campaign.status === 'processing'

  return (
    <div className="space-y-6">

      {/* Back */}
      <Link
        to="/campaigns"
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft size={16} />
        Back to campaigns
      </Link>

      {/* Header */}
      <div className="bg-white border rounded-xl p-5">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">

          <div className="min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold">
                Campaign
              </h1>

              <StatusBadge status={campaign.status} />
            </div>

            <p className="text-slate-600 text-sm max-w-3xl leading-6">
              {campaign.natural_language_input}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">

            <button
              type="button"
              onClick={() => load(true)}
              disabled={refreshing}
              title="Refresh"
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw
                size={16}
                className={refreshing ? 'animate-spin' : ''}
              />
              Refresh
            </button>

            {canStart && (
              <button
                onClick={handleStart}
                disabled={starting}
                className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
              >
                {starting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Play size={16} />
                )}

                {starting ? 'Starting...' : 'Start Discovery'}
              </button>
            )}

            {isRunning && (
              <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-2 rounded-lg text-sm font-medium">
                <Loader2 size={16} className="animate-spin" />
                Discovery Running
              </div>
            )}
          </div>
        </div>

        {/* Running message */}
        {isRunning && (
          <div className="mt-4 flex items-center gap-2 bg-blue-50 border border-blue-100 text-blue-700 rounded-lg px-4 py-3 text-sm">
            <Loader2 size={16} className="animate-spin shrink-0" />
            Discovery is running. This page will automatically refresh.
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Something went wrong</p>
            <p className="mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

        <Stat
          label="Status"
          value={campaign.status}
        />

        <Stat
          label="Businesses Found"
          value={String(campaign.total_leads_found ?? 0)}
        />

        <Stat
          label="Qualified Leads"
          value={String(campaign.qualified_leads ?? 0)}
        />

        <Stat
          label="City"
          value={params?.city || '—'}
        />

      </div>

      {/* Parsed Parameters */}
      {params && (
        <div className="bg-white border rounded-xl p-5">

          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold">
                Campaign Parameters
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Parameters extracted from your campaign description.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">

            <Parameter
              label="Country"
              value={params.country}
            />

            <Parameter
              label="City"
              value={params.city}
            />

            <Parameter
              label="Business Type"
              value={params.business_type}
            />

            <Parameter
              label="Service Offered"
              value={params.service_offered}
            />

            <Parameter
              label="Minimum Reviews"
              value={
                params.min_reviews != null
                  ? String(params.min_reviews)
                  : undefined
              }
            />

            <Parameter
              label="Maximum Results"
              value={
                params.limit != null
                  ? String(params.limit)
                  : undefined
              }
            />

            <Parameter
              label="No Website"
              value={
                params.filters?.no_website
                  ? 'Required'
                  : 'Not required'
              }
            />

            <Parameter
              label="No Booking System"
              value={
                params.filters?.no_booking
                  ? 'Required'
                  : 'Not required'
              }
            />

            <Parameter
              label="No Phone"
              value={
                params.filters?.no_phone
                  ? 'Required'
                  : 'Not required'
              }
            />

          </div>
        </div>
      )}

      {/* Leads */}
      <div>

        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold">
              Leads
              <span className="text-slate-400 font-normal ml-2">
                ({leads.length})
              </span>
            </h2>

            <p className="text-xs text-slate-500 mt-1">
              Businesses discovered and qualified for this campaign.
            </p>
          </div>
        </div>

        {leads.length === 0 ? (
          <EmptyLeads
            status={campaign.status}
            onStart={handleStart}
            canStart={canStart}
            starting={starting}
          />
        ) : (
          <LeadTable leads={leads} />
        )}

      </div>
    </div>
  )
}


/* ============================================================
   COMPONENTS
   ============================================================ */

function Stat({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <p className="text-xs text-slate-500 mb-1">
        {label}
      </p>

      <p className="text-lg font-semibold capitalize truncate">
        {value}
      </p>
    </div>
  )
}


function Parameter({
  label,
  value,
}: {
  label: string
  value?: string
}) {
  return (
    <div className="bg-slate-50 border rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">
        {label}
      </p>

      <p className="text-sm font-medium text-slate-800">
        {value || '—'}
      </p>
    </div>
  )
}


function StatusBadge({
  status,
}: {
  status: string
}) {
  const normalized = status.toLowerCase()

  let className =
    'bg-slate-100 text-slate-700'

  if (
    normalized === 'running' ||
    normalized === 'processing'
  ) {
    className =
      'bg-blue-50 text-blue-700 border border-blue-100'
  }

  if (
    normalized === 'completed' ||
    normalized === 'ready_for_review' ||
    normalized === 'success'
  ) {
    className =
      'bg-green-50 text-green-700 border border-green-100'
  }

  if (
    normalized === 'failed'
  ) {
    className =
      'bg-red-50 text-red-700 border border-red-100'
  }

  if (
    normalized === 'paused'
  ) {
    className =
      'bg-yellow-50 text-yellow-700 border border-yellow-100'
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${className}`}
    >
      {(
        normalized === 'completed' ||
        normalized === 'ready_for_review' ||
        normalized === 'success'
      ) && (
        <CheckCircle2 size={13} />
      )}

      {status.replaceAll('_', ' ')}
    </span>
  )
}


function EmptyLeads({
  status,
  onStart,
  canStart,
  starting,
}: {
  status: string
  onStart: () => void
  canStart: boolean
  starting: boolean
}) {
  const isRunning =
    status === 'running' ||
    status === 'processing'

  return (
    <div className="bg-white border rounded-xl p-8 text-center">

      {isRunning ? (
        <>
          <Loader2
            size={28}
            className="mx-auto text-brand-600 animate-spin mb-3"
          />

          <h3 className="font-medium text-slate-800">
            Discovery is running
          </h3>

          <p className="text-sm text-slate-500 mt-1">
            Searching for businesses. Results will appear automatically.
          </p>
        </>
      ) : (
        <>
          <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
            <MapPin size={20} className="text-slate-500" />
          </div>

          <h3 className="font-medium text-slate-800">
            No leads yet
          </h3>

          <p className="text-sm text-slate-500 mt-1">
            {status === 'draft'
              ? 'Start discovery to find businesses matching this campaign.'
              : 'No qualified leads were found yet.'}
          </p>

          {canStart && (
            <button
              onClick={onStart}
              disabled={starting}
              className="mt-4 inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {starting ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Play size={16} />
              )}

              {starting ? 'Starting...' : 'Start Discovery'}
            </button>
          )}
        </>
      )}

    </div>
  )
}


function LeadTable({
  leads,
}: {
  leads: Lead[]
}) {
  return (
    <div className="bg-white border rounded-xl overflow-hidden">

      <div className="overflow-x-auto">

        <table className="w-full text-sm">

          <thead className="bg-slate-50 text-slate-500 text-left">
            <tr>

              <th className="px-4 py-3 font-medium">
                Business
              </th>

              <th className="px-4 py-3 font-medium">
                Score
              </th>

              <th className="px-4 py-3 font-medium">
                Stage
              </th>

              <th className="px-4 py-3 font-medium">
                Category
              </th>

              <th className="px-4 py-3 font-medium">
                Phone
              </th>

              <th className="px-4 py-3 font-medium">
                Website
              </th>

            </tr>
          </thead>

          <tbody>

            {leads.map((lead) => (
              <LeadRow
                key={lead.id}
                lead={lead}
              />
            ))}

          </tbody>

        </table>

      </div>
    </div>
  )
}


function LeadRow({
  lead,
}: {
  lead: Lead
}) {
  const score =
    lead.opportunity_score != null
      ? Math.round(lead.opportunity_score)
      : null

  return (
    <tr className="border-t hover:bg-slate-50">

      {/* Business */}
      <td className="px-4 py-3 min-w-[220px]">

        <Link
          to={`/leads/${lead.id}`}
          className="text-brand-600 hover:underline font-medium"
        >
          {lead.business_name || lead.business_id.slice(0, 8)}
        </Link>

        {lead.business_address && (
          <div className="flex items-start gap-1 mt-1 text-xs text-slate-400">
            <MapPin size={12} className="mt-0.5 shrink-0" />
            <span className="line-clamp-2">
              {lead.business_address}
            </span>
          </div>
        )}

      </td>

      {/* Score */}
      <td className="px-4 py-3">

        {score != null ? (
          <ScoreBadge score={score} />
        ) : (
          '—'
        )}

      </td>

      {/* Stage */}
      <td className="px-4 py-3">

        <span className="capitalize">
          {lead.stage.replaceAll('_', ' ')}
        </span>

      </td>

      {/* Category */}
      <td className="px-4 py-3 text-slate-500">
        {lead.business_category || '—'}
      </td>

      {/* Phone */}
      <td className="px-4 py-3">

        {lead.business_phone ? (
          <a
            href={`tel:${lead.business_phone}`}
            className="inline-flex items-center gap-1 text-slate-700 hover:text-brand-600"
          >
            <Phone size={14} />
            {lead.business_phone}
          </a>
        ) : (
          <span className="text-slate-400">
            —
          </span>
        )}

      </td>

      {/* Website */}
      <td className="px-4 py-3">

        {lead.business_website ? (
          <a
            href={lead.business_website}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-brand-600 hover:underline"
          >
            <Globe size={14} />
            Website
            <ExternalLink size={12} />
          </a>
        ) : (
          <span className="text-slate-400">
            No website
          </span>
        )}

      </td>

    </tr>
  )
}


function ScoreBadge({
  score,
}: {
  score: number
}) {
  let className =
    'bg-slate-100 text-slate-700'

  if (score >= 80) {
    className =
      'bg-green-50 text-green-700'
  } else if (score >= 60) {
    className =
      'bg-blue-50 text-blue-700'
  } else if (score >= 40) {
    className =
      'bg-yellow-50 text-yellow-700'
  } else {
    className =
      'bg-red-50 text-red-700'
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold ${className}`}
    >
      {score}
    </span>
  )
}