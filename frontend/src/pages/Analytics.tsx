import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3,
  Users,
  Target,
  Mail,
  MessageSquare,
  Trophy,
  TrendingUp,
  ArrowUpRight,
  Megaphone,
  RefreshCw,
} from 'lucide-react'

import { api } from '../lib/api'
import { Campaign, Lead } from '../types'

type AnalyticsData = {
  campaigns: Campaign[]
  leads: Lead[]
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData>({
    campaigns: [],
    leads: [],
  })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const load = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)

    setError('')

    try {
      const campaignData = await api.listCampaigns()

      const campaignLeads = await Promise.all(
        campaignData.items.map(async (campaign) => {
          try {
            const result = await api.listCampaignLeads(campaign.id)
            return result.items
          } catch {
            return []
          }
        }),
      )

      setData({
        campaigns: campaignData.items,
        leads: campaignLeads.flat(),
      })
    } catch (e: unknown) {
      const err = e as { message?: string }
      setError(err.message || 'Failed to load analytics')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const stats = useMemo(() => {
    const { campaigns, leads } = data

    const qualified = leads.filter(
      (lead) =>
        lead.stage !== 'disqualified' &&
        lead.stage !== 'do_not_contact',
    )

    const contacted = leads.filter(
      (lead) =>
        lead.stage === 'contacted' ||
        lead.stage === 'follow_up' ||
        lead.stage === 'replied' ||
        lead.stage === 'interested' ||
        lead.stage === 'won',
    )

    const replied = leads.filter(
      (lead) =>
        lead.stage === 'replied' ||
        lead.stage === 'interested' ||
        lead.stage === 'won',
    )

    const interested = leads.filter(
      (lead) =>
        lead.stage === 'interested' ||
        lead.stage === 'won',
    )

    const won = leads.filter((lead) => lead.stage === 'won')

    const lost = leads.filter((lead) => lead.stage === 'lost')

    const replyRate =
      contacted.length > 0
        ? (replied.length / contacted.length) * 100
        : 0

    const conversionRate =
      qualified.length > 0
        ? (won.length / qualified.length) * 100
        : 0

    const averageScore =
      leads.length > 0
        ? leads.reduce(
            (sum, lead) =>
              sum + (Number(lead.opportunity_score) || 0),
            0,
          ) / leads.length
        : 0

    return {
      campaigns: campaigns.length,
      totalLeads: leads.length,
      qualified: qualified.length,
      contacted: contacted.length,
      replied: replied.length,
      interested: interested.length,
      won: won.length,
      lost: lost.length,
      replyRate,
      conversionRate,
      averageScore,
    }
  }, [data])

  const stageCounts = useMemo(() => {
    const stages = [
      'new',
      'contacted',
      'follow_up',
      'replied',
      'interested',
      'won',
      'lost',
      'disqualified',
      'do_not_contact',
    ]

    return stages.map((stage) => ({
      stage,
      count: data.leads.filter(
        (lead) => (lead.stage || 'new') === stage,
      ).length,
    }))
  }, [data.leads])

  const maxStageCount = Math.max(
    ...stageCounts.map((item) => item.count),
    1,
  )

  const campaignPerformance = useMemo(() => {
    return data.campaigns
      .map((campaign) => {
        const leads = data.leads.filter(
          (lead) => lead.campaign_id === campaign.id,
        )

        const won = leads.filter(
          (lead) => lead.stage === 'won',
        ).length

        const replied = leads.filter(
          (lead) =>
            lead.stage === 'replied' ||
            lead.stage === 'interested' ||
            lead.stage === 'won',
        ).length

        return {
          ...campaign,
          leads: leads.length,
          won,
          replied,
        }
      })
      .sort((a, b) => b.leads - a.leads)
      .slice(0, 5)
  }, [data])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-slate-100 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-white border rounded-2xl p-5 h-32 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 size={24} className="text-brand-600" />
            <h1 className="text-2xl font-bold text-slate-900">
              Analytics
            </h1>
          </div>

          <p className="text-sm text-slate-500 mt-1">
            Track your lead generation and outreach performance.
          </p>
        </div>

        <button
          type="button"
          onClick={() => load(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 border bg-white px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw
            size={15}
            className={refreshing ? 'animate-spin' : ''}
          />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Main stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={<Megaphone size={20} />}
          label="Campaigns"
          value={stats.campaigns}
          description="Total campaigns"
        />

        <StatCard
          icon={<Users size={20} />}
          label="Total Leads"
          value={stats.totalLeads}
          description="Discovered leads"
        />

        <StatCard
          icon={<Target size={20} />}
          label="Qualified Leads"
          value={stats.qualified}
          description="Active opportunities"
        />

        <StatCard
          icon={<Trophy size={20} />}
          label="Won"
          value={stats.won}
          description="Converted leads"
        />
      </div>

      {/* Performance stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          icon={<Mail size={19} />}
          label="Contacted"
          value={stats.contacted}
        />

        <MetricCard
          icon={<MessageSquare size={19} />}
          label="Replies"
          value={stats.replied}
        />

        <MetricCard
          icon={<TrendingUp size={19} />}
          label="Reply Rate"
          value={`${stats.replyRate.toFixed(1)}%`}
        />

        <MetricCard
          icon={<ArrowUpRight size={19} />}
          label="Conversion Rate"
          value={`${stats.conversionRate.toFixed(1)}%`}
        />
      </div>

      {/* Funnel */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white border rounded-2xl p-5">
          <div className="mb-5">
            <h2 className="font-semibold text-slate-900">
              Lead Funnel
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Current lead progression
            </p>
          </div>

          <div className="space-y-4">
            <FunnelRow
              label="Total Leads"
              value={stats.totalLeads}
              percentage={100}
            />

            <FunnelRow
              label="Qualified"
              value={stats.qualified}
              percentage={
                stats.totalLeads
                  ? (stats.qualified / stats.totalLeads) * 100
                  : 0
              }
            />

            <FunnelRow
              label="Contacted"
              value={stats.contacted}
              percentage={
                stats.totalLeads
                  ? (stats.contacted / stats.totalLeads) * 100
                  : 0
              }
            />

            <FunnelRow
              label="Replied"
              value={stats.replied}
              percentage={
                stats.totalLeads
                  ? (stats.replied / stats.totalLeads) * 100
                  : 0
              }
            />

            <FunnelRow
              label="Interested"
              value={stats.interested}
              percentage={
                stats.totalLeads
                  ? (stats.interested / stats.totalLeads) * 100
                  : 0
              }
            />

            <FunnelRow
              label="Won"
              value={stats.won}
              percentage={
                stats.totalLeads
                  ? (stats.won / stats.totalLeads) * 100
                  : 0
              }
            />
          </div>
        </div>

        {/* Stage distribution */}
        <div className="bg-white border rounded-2xl p-5">
          <div className="mb-5">
            <h2 className="font-semibold text-slate-900">
              Pipeline Distribution
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Leads by current stage
            </p>
          </div>

          <div className="space-y-3">
            {stageCounts.map((item) => (
              <div key={item.stage}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-600 capitalize">
                    {item.stage.replace(/_/g, ' ')}
                  </span>

                  <span className="font-medium text-slate-800">
                    {item.count}
                  </span>
                </div>

                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-600 rounded-full transition-all"
                    style={{
                      width: `${(item.count / maxStageCount) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Campaign performance */}
      <div className="bg-white border rounded-2xl overflow-hidden">
        <div className="p-5 border-b">
          <h2 className="font-semibold text-slate-900">
            Campaign Performance
          </h2>

          <p className="text-xs text-slate-500 mt-1">
            Top campaigns by discovered leads
          </p>
        </div>

        {campaignPerformance.length === 0 ? (
          <div className="p-10 text-center">
            <Megaphone
              size={32}
              className="mx-auto text-slate-300 mb-3"
            />

            <p className="text-sm text-slate-500">
              No campaign data yet.
            </p>

            <Link
              to="/campaigns/new"
              className="inline-block mt-2 text-sm text-brand-600 hover:underline"
            >
              Create your first campaign
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr>
                  <th className="px-5 py-3 font-medium">
                    Campaign
                  </th>

                  <th className="px-5 py-3 font-medium">
                    Leads
                  </th>

                  <th className="px-5 py-3 font-medium">
                    Replies
                  </th>

                  <th className="px-5 py-3 font-medium">
                    Won
                  </th>

                  <th className="px-5 py-3 font-medium">
                    Status
                  </th>
                </tr>
              </thead>

              <tbody>
                {campaignPerformance.map((campaign) => (
                  <tr
                    key={campaign.id}
                    className="border-t hover:bg-slate-50"
                  >
                    <td className="px-5 py-3">
                      <Link
                        to={`/campaigns/${campaign.id}`}
                        className="text-brand-600 hover:underline font-medium"
                      >
                        {campaign.natural_language_input?.slice(
                          0,
                          55,
                        ) || 'Campaign'}

                        {(campaign.natural_language_input?.length || 0) >
                          55 && '…'}
                      </Link>
                    </td>

                    <td className="px-5 py-3 font-medium">
                      {campaign.leads}
                    </td>

                    <td className="px-5 py-3">
                      {campaign.replied}
                    </td>

                    <td className="px-5 py-3">
                      {campaign.won}
                    </td>

                    <td className="px-5 py-3">
                      <StatusBadge status={campaign.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Extra metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border rounded-2xl p-5">
          <h2 className="font-semibold mb-4">
            Lead Quality
          </h2>

          <div className="flex items-end gap-3">
            <span className="text-4xl font-bold text-slate-900">
              {stats.averageScore.toFixed(0)}
            </span>

            <span className="text-sm text-slate-500 mb-1">
              average opportunity score
            </span>
          </div>

          <div className="mt-4 h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 rounded-full"
              style={{
                width: `${Math.min(stats.averageScore, 100)}%`,
              }}
            />
          </div>
        </div>

        <div className="bg-white border rounded-2xl p-5">
          <h2 className="font-semibold mb-4">
            Outcome
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <MiniMetric
              label="Interested"
              value={stats.interested}
            />

            <MiniMetric
              label="Won"
              value={stats.won}
            />

            <MiniMetric
              label="Lost"
              value={stats.lost}
            />

            <MiniMetric
              label="Replies"
              value={stats.replied}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  description,
}: {
  icon: React.ReactNode
  label: string
  value: number
  description: string
}) {
  return (
    <div className="bg-white border rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          {icon}
          <span>{label}</span>
        </div>

        <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-500">
          {icon}
        </div>
      </div>

      <p className="text-3xl font-bold text-slate-900">
        {value.toLocaleString()}
      </p>

      <p className="text-xs text-slate-500 mt-1">
        {description}
      </p>
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
}) {
  return (
    <div className="bg-white border rounded-2xl p-4">
      <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
        {icon}
        {label}
      </div>

      <p className="text-2xl font-bold text-slate-900">
        {typeof value === 'number'
          ? value.toLocaleString()
          : value}
      </p>
    </div>
  )
}

function FunnelRow({
  label,
  value,
  percentage,
}: {
  label: string
  value: number
  percentage: number
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="text-slate-600">
          {label}
        </span>

        <span className="font-semibold text-slate-900">
          {value.toLocaleString()}
        </span>
      </div>

      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-600 rounded-full"
          style={{
            width: `${Math.min(Math.max(percentage, 0), 100)}%`,
          }}
        />
      </div>

      <p className="text-[11px] text-slate-400 mt-1">
        {percentage.toFixed(1)}%
      </p>
    </div>
  )
}

function MiniMetric({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="bg-slate-50 rounded-xl p-3">
      <p className="text-xs text-slate-500">
        {label}
      </p>

      <p className="text-xl font-bold mt-1">
        {value.toLocaleString()}
      </p>
    </div>
  )
}

function StatusBadge({
  status,
}: {
  status: string
}) {
  const colors: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    failed: 'bg-red-100 text-red-700',
  }

  return (
    <span
      className={`inline-flex px-2 py-1 rounded-md text-xs font-medium ${
        colors[status] || colors.draft
      }`}
    >
      {status}
    </span>
  )
}