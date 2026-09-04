import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Campaign } from '../types'
import {
  Plus,
  RefreshCw,
  ChevronRight,
  Target,
  Users,
  CheckCircle2,
  Clock3,
  AlertCircle,
} from 'lucide-react'
import { EmptyState, ErrorBanner } from '../components/ui'

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const loadCampaigns = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    setError('')

    try {
      const data = await api.listCampaigns()
      setCampaigns(data.items || [])
    } catch (err: any) {
      console.error(err)
      setError(err?.message || 'Failed to load campaigns')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadCampaigns()
  }, [loadCampaigns])

  if (loading) {
    return <CampaignsSkeleton />
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Campaigns
          </h1>

          <p className="text-sm text-slate-500 mt-1">
            Create and manage your lead discovery campaigns.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => loadCampaigns(true)}
            disabled={refreshing}
            title="Refresh campaigns"
            className="inline-flex items-center justify-center w-10 h-10 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition"
          >
            <RefreshCw
              size={16}
              className={refreshing ? 'animate-spin' : ''}
            />
          </button>

          <Link
            to="/campaigns/new"
            className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 transition"
          >
            <Plus size={17} />
            New Campaign
          </Link>
        </div>
      </div>

      {/* Error */}
      {error && (
        <ErrorBanner
          message={error}
          onRetry={() => loadCampaigns()}
          onDismiss={() => setError('')}
        />
      )}

      {/* Summary */}
      {campaigns.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <SummaryCard
            icon={<Target size={18} />}
            label="Total Campaigns"
            value={campaigns.length}
          />

          <SummaryCard
            icon={<Users size={18} />}
            label="Leads Found"
            value={campaigns.reduce(
              (sum, campaign) => sum + (campaign.total_leads_found || 0),
              0
            )}
          />

          <SummaryCard
            icon={<CheckCircle2 size={18} />}
            label="Qualified Leads"
            value={campaigns.reduce(
              (sum, campaign) => sum + (campaign.qualified_leads || 0),
              0
            )}
          />
        </div>
      )}

      {/* Empty State */}
      {campaigns.length === 0 ? (
        <EmptyState
          icon={<Target size={28} />}
          title="No campaigns yet"
          description="Create your first campaign and describe the type of businesses you want the AI to discover."
          actionLabel="Create Campaign"
          actionTo="/campaigns/new"
        />
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden md:block bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr className="text-left text-slate-500">
                  <th className="px-5 py-3.5 font-medium">
                    Campaign
                  </th>

                  <th className="px-4 py-3.5 font-medium">
                    Status
                  </th>

                  <th className="px-4 py-3.5 font-medium text-center">
                    Found
                  </th>

                  <th className="px-4 py-3.5 font-medium text-center">
                    Qualified
                  </th>

                  <th className="px-4 py-3.5 font-medium">
                    Created
                  </th>

                  <th className="px-4 py-3.5"></th>
                </tr>
              </thead>

              <tbody>
                {campaigns.map((campaign) => (
                  <CampaignRow
                    key={campaign.id}
                    campaign={campaign}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards */}
          <div className="md:hidden space-y-3">
            {campaigns.map((campaign) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/* -------------------------------------------------------
   Desktop Row
------------------------------------------------------- */

function CampaignRow({
  campaign,
}: {
  campaign: Campaign
}) {
  const found = campaign.total_leads_found || 0
  const qualified = campaign.qualified_leads || 0

  const qualificationRate =
    found > 0
      ? Math.round((qualified / found) * 100)
      : 0

  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50 transition">
      {/* Description */}
      <td className="px-5 py-4 max-w-md">
        <Link
          to={`/campaigns/${campaign.id}`}
          className="group block"
        >
          <p className="font-medium text-slate-800 group-hover:text-brand-600 transition line-clamp-2">
            {campaign.natural_language_input}
          </p>

          <p className="text-xs text-slate-400 mt-1">
            ID: {campaign.id.slice(0, 8)}...
          </p>
        </Link>
      </td>

      {/* Status */}
      <td className="px-4 py-4">
        <StatusBadge status={campaign.status} />
      </td>

      {/* Found */}
      <td className="px-4 py-4 text-center">
        <div className="font-semibold text-slate-800">
          {found}
        </div>

        <div className="text-xs text-slate-400">
          leads
        </div>
      </td>

      {/* Qualified */}
      <td className="px-4 py-4 text-center">
        <div className="font-semibold text-slate-800">
          {qualified}
        </div>

        {found > 0 && (
          <div className="text-xs text-green-600">
            {qualificationRate}%
          </div>
        )}
      </td>

      {/* Created */}
      <td className="px-4 py-4 text-slate-500">
        <div>
          {formatDate(campaign.created_at)}
        </div>

        <div className="text-xs text-slate-400 mt-0.5">
          {formatTime(campaign.created_at)}
        </div>
      </td>

      {/* Arrow */}
      <td className="px-4 py-4">
        <Link
          to={`/campaigns/${campaign.id}`}
          className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition"
        >
          <ChevronRight size={17} />
        </Link>
      </td>
    </tr>
  )
}

/* -------------------------------------------------------
   Mobile Card
------------------------------------------------------- */

function CampaignCard({
  campaign,
}: {
  campaign: Campaign
}) {
  const found = campaign.total_leads_found || 0
  const qualified = campaign.qualified_leads || 0

  const qualificationRate =
    found > 0
      ? Math.round((qualified / found) * 100)
      : 0

  return (
    <Link
      to={`/campaigns/${campaign.id}`}
      className="block bg-white border border-slate-200 rounded-xl p-4 hover:border-brand-300 hover:shadow-sm transition"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium text-slate-800 text-sm leading-5 line-clamp-3">
          {campaign.natural_language_input}
        </p>

        <ChevronRight
          size={18}
          className="text-slate-400 shrink-0 mt-0.5"
        />
      </div>

      <div className="mt-3">
        <StatusBadge status={campaign.status} />
      </div>

      <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-100">
        <div>
          <p className="text-xs text-slate-400">
            Found
          </p>

          <p className="font-semibold text-slate-800 mt-1">
            {found}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Qualified
          </p>

          <p className="font-semibold text-slate-800 mt-1">
            {qualified}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Rate
          </p>

          <p className="font-semibold text-green-600 mt-1">
            {qualificationRate}%
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-4">
        <Clock3 size={13} />
        {formatDate(campaign.created_at)}
      </div>
    </Link>
  )
}

/* -------------------------------------------------------
   Status Badge
------------------------------------------------------- */

function StatusBadge({
  status,
}: {
  status: string
}) {
  const normalized = (status || 'unknown').toLowerCase()

  const config: Record<
    string,
    {
      label: string
      className: string
      dot: string
    }
  > = {
    draft: {
      label: 'Draft',
      className: 'bg-slate-100 text-slate-600',
      dot: 'bg-slate-400',
    },

    running: {
      label: 'Running',
      className: 'bg-blue-50 text-blue-700',
      dot: 'bg-blue-500 animate-pulse',
    },

    processing: {
      label: 'Processing',
      className: 'bg-blue-50 text-blue-700',
      dot: 'bg-blue-500 animate-pulse',
    },

    ready_for_review: {
      label: 'Ready for Review',
      className: 'bg-green-50 text-green-700',
      dot: 'bg-green-500',
    },

    completed: {
      label: 'Completed',
      className: 'bg-green-50 text-green-700',
      dot: 'bg-green-500',
    },

    paused: {
      label: 'Paused',
      className: 'bg-amber-50 text-amber-700',
      dot: 'bg-amber-500',
    },

    failed: {
      label: 'Failed',
      className: 'bg-red-50 text-red-700',
      dot: 'bg-red-500',
    },

    cancelled: {
      label: 'Cancelled',
      className: 'bg-slate-100 text-slate-600',
      dot: 'bg-slate-400',
    },
  }

  const current = config[normalized] || {
    label: status || 'Unknown',
    className: 'bg-slate-100 text-slate-600',
    dot: 'bg-slate-400',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${current.className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${current.dot}`}
      />

      {current.label}
    </span>
  )
}

/* -------------------------------------------------------
   Summary Card
------------------------------------------------------- */

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: number
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
          {icon}
        </div>

        <div>
          <p className="text-xs text-slate-500">
            {label}
          </p>

          <p className="text-xl font-bold text-slate-900 mt-0.5">
            {value.toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------
   Loading Skeleton
------------------------------------------------------- */

function CampaignsSkeleton() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="h-7 w-32 bg-slate-200 rounded animate-pulse" />
          <div className="h-4 w-64 bg-slate-100 rounded mt-2 animate-pulse" />
        </div>

        <div className="h-10 w-32 bg-slate-200 rounded-lg animate-pulse" />
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="h-12 bg-slate-50 border-b border-slate-200" />

        {[1, 2, 3, 4, 5].map((item) => (
          <div
            key={item}
            className="h-20 border-b border-slate-100 flex items-center gap-6 px-5"
          >
            <div className="h-4 w-64 bg-slate-100 rounded animate-pulse" />
            <div className="h-6 w-20 bg-slate-100 rounded-full animate-pulse" />
            <div className="h-4 w-10 bg-slate-100 rounded animate-pulse" />
            <div className="h-4 w-10 bg-slate-100 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}

/* -------------------------------------------------------
   Date Helpers
------------------------------------------------------- */

function formatDate(date: string) {
  return new Date(date).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatTime(date: string) {
  return new Date(date).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  })
}