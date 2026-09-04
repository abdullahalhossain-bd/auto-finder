import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Lead, Campaign } from '../types'
import {
  RefreshCw,
  Search,
  Users,
  ChevronDown,
} from 'lucide-react'
import { PageSkeleton, CardListSkeleton, EmptyState, ErrorBanner } from '../components/ui'
import { Confetti } from '../components/Confetti'

const STAGES = [
  'new',
  'contacted',
  'follow_up',
  'replied',
  'interested',
  'won',
  'lost',
  'disqualified',
  'do_not_contact',
] as const

type Stage = (typeof STAGES)[number]

const STAGE_CONFIG: Record<
  Stage,
  {
    label: string
    header: string
    badge: string
    dot: string
  }
> = {
  new: {
    label: 'New',
    header: 'bg-slate-100',
    badge: 'bg-slate-200 text-slate-700',
    dot: 'bg-slate-400',
  },
  contacted: {
    label: 'Contacted',
    header: 'bg-blue-50',
    badge: 'bg-blue-100 text-blue-700',
    dot: 'bg-blue-500',
  },
  follow_up: {
    label: 'Follow Up',
    header: 'bg-purple-50',
    badge: 'bg-purple-100 text-purple-700',
    dot: 'bg-purple-500',
  },
  replied: {
    label: 'Replied',
    header: 'bg-cyan-50',
    badge: 'bg-cyan-100 text-cyan-700',
    dot: 'bg-cyan-500',
  },
  interested: {
    label: 'Interested',
    header: 'bg-amber-50',
    badge: 'bg-amber-100 text-amber-700',
    dot: 'bg-amber-500',
  },
  won: {
    label: 'Won',
    header: 'bg-green-50',
    badge: 'bg-green-100 text-green-700',
    dot: 'bg-green-500',
  },
  lost: {
    label: 'Lost',
    header: 'bg-red-50',
    badge: 'bg-red-100 text-red-700',
    dot: 'bg-red-500',
  },
  disqualified: {
    label: 'Disqualified',
    header: 'bg-orange-50',
    badge: 'bg-orange-100 text-orange-700',
    dot: 'bg-orange-500',
  },
  do_not_contact: {
    label: 'Do Not Contact',
    header: 'bg-rose-50',
    badge: 'bg-rose-100 text-rose-700',
    dot: 'bg-rose-500',
  },
}

export default function Pipeline() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [campaignId, setCampaignId] = useState('')
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [movingLeadId, setMovingLeadId] = useState<string | null>(null)
  const [celebrateKey, setCelebrateKey] = useState(0)

  useEffect(() => {
    if (celebrateKey === 0) return
    const t = setTimeout(() => setCelebrateKey(0), 2400)
    return () => clearTimeout(t)
  }, [celebrateKey])
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  const loadCampaigns = async () => {
    const data = await api.listCampaigns()
    setCampaigns(data.items)

    if (!campaignId && data.items[0]) {
      setCampaignId(data.items[0].id)
    }
  }

  const loadLeads = async (cid: string) => {
    if (!cid) {
      setLeads([])
      return
    }

    const data = await api.listCampaignLeads(cid)
    setLeads(data.items)
  }

  useEffect(() => {
    const init = async () => {
      try {
        setError('')
        await loadCampaigns()
      } catch (e: any) {
        setError(e.message || 'Failed to load campaigns')
      } finally {
        setLoading(false)
      }
    }

    init()
  }, [])

  useEffect(() => {
    if (!campaignId) return

    const load = async () => {
      try {
        setError('')
        await loadLeads(campaignId)
      } catch (e: any) {
        setError(e.message || 'Failed to load leads')
      }
    }

    load()
  }, [campaignId])

  const refresh = async () => {
    try {
      setRefreshing(true)
      setError('')

      if (campaignId) {
        await loadLeads(campaignId)
      } else {
        await loadCampaigns()
      }
    } catch (e: any) {
      setError(e.message || 'Refresh failed')
    } finally {
      setRefreshing(false)
    }
  }

  const filteredLeads = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) return leads

    return leads.filter((lead) => {
      const name = lead.business_name?.toLowerCase() || ''
      const category = lead.business_category?.toLowerCase() || ''
      const id = lead.id.toLowerCase()

      return (
        name.includes(query) ||
        category.includes(query) ||
        id.includes(query)
      )
    })
  }, [leads, search])

  const byStage = (stage: Stage) =>
    filteredLeads.filter((lead) => (lead.stage || 'new') === stage)

  const move = async (leadId: string, stage: Stage) => {
    const previousLead = leads.find((lead) => lead.id === leadId)

    if (!previousLead || previousLead.stage === stage) return

    setError('')
    setMovingLeadId(leadId)

    // Optimistic UI update
    setLeads((current) =>
      current.map((lead) =>
        lead.id === leadId
          ? { ...lead, stage }
          : lead,
      ),
    )

    try {
      await api.setLeadStage(leadId, stage)
      if (stage === 'won') {
        setCelebrateKey((k) => k + 1)
      }
    } catch (e: any) {
      // Rollback if API fails
      setLeads((current) =>
        current.map((lead) =>
          lead.id === leadId
            ? {
                ...lead,
                stage: previousLead.stage,
              }
            : lead,
        ),
      )

      setError(e.message || 'Stage change failed')
    } finally {
      setMovingLeadId(null)
    }
  }

  const selectedCampaign = campaigns.find(
    (campaign) => campaign.id === campaignId,
  )

  const stageCounts = useMemo(() => {
    const counts: Record<string, number> = {}

    STAGES.forEach((stage) => {
      counts[stage] = leads.filter(
        (lead) => (lead.stage || 'new') === stage,
      ).length
    })

    return counts
  }, [leads])

  const activeLeads = leads.filter(
    (lead) =>
      lead.stage !== 'lost' &&
      lead.stage !== 'disqualified' &&
      lead.stage !== 'do_not_contact',
  ).length

  const wonLeads = stageCounts.won || 0

  const averageScore =
    leads.length > 0
      ? Math.round(
          leads.reduce(
            (sum, lead) =>
              sum + (lead.opportunity_score || 0),
            0,
          ) / leads.length,
        )
      : 0

  if (loading) {
    return <PageSkeleton />
  }

  return (
    <div className="min-w-0">
      {celebrateKey > 0 && <Confetti key={celebrateKey} />}
      {/* Header */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Pipeline
          </h1>

          <p className="text-sm text-slate-500 mt-1">
            Manage your leads through the sales process.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={refresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 border bg-white px-3 py-2 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw
              size={15}
              className={refreshing ? 'animate-spin' : ''}
            />
            Refresh
          </button>

          <select
            className="border bg-white rounded-lg px-3 py-2 text-sm max-w-[280px]"
            value={campaignId}
            onChange={(e) => setCampaignId(e.target.value)}
          >
            <option value="">Select campaign</option>

            {campaigns.map((campaign) => (
              <option
                key={campaign.id}
                value={campaign.id}
              >
                {campaign.natural_language_input?.slice(0, 55) ||
                  campaign.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm flex items-center justify-between">
          <span>{error}</span>

          <button
            type="button"
            onClick={() => setError('')}
            className="text-red-500 hover:text-red-700 ml-4"
          >
            ×
          </button>
        </div>
      )}

      {!campaignId ? (
        <div className="bg-white border rounded-xl p-10 text-center">
          <Users
            size={32}
            className="mx-auto text-slate-400 mb-3"
          />

          <h2 className="font-semibold text-slate-800 mb-1">
            No campaign selected
          </h2>

          <p className="text-sm text-slate-500 mb-4">
            Create a campaign first, then manage its leads here.
          </p>

          <Link
            to="/campaigns/new"
            className="inline-flex bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700"
          >
            Create Campaign
          </Link>
        </div>
      ) : (
        <>
          {/* Campaign info */}
          {selectedCampaign && (
            <div className="bg-white border rounded-xl px-4 py-3 mb-4">
              <div className="text-xs text-slate-500 mb-1">
                Current campaign
              </div>

              <Link
                to={`/campaigns/${selectedCampaign.id}`}
                className="text-sm font-medium text-brand-700 hover:underline"
              >
                {selectedCampaign.natural_language_input}
              </Link>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <PipelineStat
              label="Total Leads"
              value={leads.length}
            />

            <PipelineStat
              label="Active"
              value={activeLeads}
            />

            <PipelineStat
              label="Won"
              value={wonLeads}
            />

            <PipelineStat
              label="Avg. Score"
              value={averageScore || '—'}
            />
          </div>

          {/* Search */}
          <div className="relative mb-5 max-w-md">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search businesses or category…"
              className="w-full border bg-white rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />

            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            )}
          </div>

          {/* Pipeline board */}
          <div className="flex gap-3 overflow-x-auto pb-5 items-start">
            {STAGES.map((stage) => {
              const config = STAGE_CONFIG[stage]
              const stageLeads = byStage(stage)

              return (
                <div
                  key={stage}
                  className="w-[270px] min-w-[270px] bg-slate-50 border rounded-xl overflow-hidden flex-shrink-0"
                >
                  {/* Column header */}
                  <div
                    className={`px-3 py-3 ${config.header}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full ${config.dot}`}
                        />

                        <span className="text-xs font-semibold uppercase text-slate-700">
                          {config.label}
                        </span>
                      </div>

                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${config.badge}`}
                      >
                        {stageLeads.length}
                      </span>
                    </div>
                  </div>

                  {/* Cards */}
                  <div className="p-2 space-y-2 max-h-[65vh] overflow-y-auto">
                    {stageLeads.length === 0 ? (
                      <div className="text-center py-10 px-2" role="status">
                        <p className="text-xs font-medium text-slate-400">No leads</p>
                        <p className="text-[11px] text-slate-400 mt-1">
                          Move leads here from other stages
                        </p>
                      </div>
                    ) : (
                      stageLeads.map((lead) => (
                        <LeadCard
                          key={lead.id}
                          lead={lead}
                          moving={movingLeadId === lead.id}
                          onMove={move}
                        />
                      ))
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

function LeadCard({
  lead,
  moving,
  onMove,
}: {
  lead: Lead
  moving: boolean
  onMove: (leadId: string, stage: Stage) => void
}) {
  const score =
    lead.opportunity_score != null
      ? Math.round(lead.opportunity_score)
      : null

  const scoreClass =
    score == null
      ? 'text-slate-400'
      : score >= 80
        ? 'text-green-700'
        : score >= 60
          ? 'text-amber-700'
          : 'text-slate-600'

  return (
    <div
      className={`bg-white border rounded-lg p-3 shadow-sm transition ${
        moving ? 'opacity-60' : 'hover:shadow-md'
      }`}
    >
      {/* Business */}
      <div className="flex items-start justify-between gap-2">
        <Link
          to={`/leads/${lead.id}`}
          className="font-medium text-sm text-slate-900 hover:text-brand-700 line-clamp-2"
        >
          {lead.business_name || `Lead ${lead.id.slice(0, 8)}`}
        </Link>

        {score != null && (
          <span
            className={`text-xs font-bold whitespace-nowrap ${scoreClass}`}
          >
            {score}
          </span>
        )}
      </div>

      {/* Category */}
      {lead.business_category && (
        <div className="text-xs text-slate-500 mt-1 truncate">
          {lead.business_category}
        </div>
      )}

      {/* Score */}
      <div className="flex items-center justify-between mt-3">
        <span className="text-[11px] text-slate-400">
          Opportunity score
        </span>

        <span className={`text-xs font-semibold ${scoreClass}`}>
          {score ?? '—'}
        </span>
      </div>

      {/* Stage selector */}
      <div className="relative mt-2">
        <select
          disabled={moving}
          value={lead.stage || 'new'}
          onChange={(e) =>
            onMove(
              lead.id,
              e.target.value as Stage,
            )
          }
          className="w-full appearance-none border rounded-lg bg-white px-2.5 py-1.5 pr-7 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
        >
          {STAGES.map((stage) => (
            <option key={stage} value={stage}>
              {STAGE_CONFIG[stage].label}
            </option>
          ))}
        </select>

        <ChevronDown
          size={13}
          className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400"
        />
      </div>

      {moving && (
        <p className="text-[11px] text-slate-400 mt-2">
          Updating…
        </p>
      )}
    </div>
  )
}

function PipelineStat({
  label,
  value,
}: {
  label: string
  value: number | string
}) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <p className="text-xs text-slate-500 mb-1">
        {label}
      </p>

      <p className="text-2xl font-bold text-slate-900">
        {value}
      </p>
    </div>
  )
}