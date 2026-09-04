import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Lead, Campaign } from '../types'
import {
  Search,
  Filter,
  Users,
  ExternalLink,
  ChevronDown,
} from 'lucide-react'

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
]

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [search, setSearch] = useState('')
  const [stage, setStage] = useState('')
  const [campaignId, setCampaignId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError('')

      try {
        const campaignsData = await api.listCampaigns()
        setCampaigns(campaignsData.items)

        const all: Lead[] = []

        for (const campaign of campaignsData.items) {
          try {
            const data = await api.listCampaignLeads(campaign.id)
            all.push(...data.items)
          } catch {
            // Ignore individual campaign failures
          }
        }

        setLeads(all)
      } catch (e: any) {
        setError(e.message || 'Failed to load leads')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  const filteredLeads = useMemo(() => {
    const q = search.trim().toLowerCase()

    return leads.filter((lead) => {
      const matchesSearch =
        !q ||
        lead.business_name?.toLowerCase().includes(q) ||
        lead.business_category?.toLowerCase().includes(q) ||
        lead.business_id?.toLowerCase().includes(q)

      const matchesStage =
        !stage || lead.stage === stage

      const matchesCampaign =
        !campaignId || lead.campaign_id === campaignId

      return matchesSearch && matchesStage && matchesCampaign
    })
  }, [leads, search, stage, campaignId])

  const getCampaignName = (id: string) => {
    const campaign = campaigns.find((c) => c.id === id)

    if (!campaign) return id.slice(0, 8)

    return campaign.natural_language_input.length > 35
      ? `${campaign.natural_language_input.slice(0, 35)}…`
      : campaign.natural_language_input
  }

  const stageClass = (value: string) => {
    const colors: Record<string, string> = {
      new: 'bg-slate-100 text-slate-700',
      contacted: 'bg-blue-100 text-blue-700',
      follow_up: 'bg-yellow-100 text-yellow-700',
      replied: 'bg-purple-100 text-purple-700',
      interested: 'bg-indigo-100 text-indigo-700',
      won: 'bg-green-100 text-green-700',
      lost: 'bg-red-100 text-red-700',
      disqualified: 'bg-red-100 text-red-700',
      do_not_contact: 'bg-slate-200 text-slate-600',
    }

    return colors[value] || colors.new
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-32 bg-slate-100 rounded animate-pulse" />
        <div className="h-16 bg-slate-100 rounded-xl animate-pulse" />
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Leads
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage, qualify and track all discovered prospects.
          </p>
        </div>

        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Users size={18} />
          <span>
            {filteredLeads.length} of {leads.length}
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border rounded-xl p-4 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search */}
          <div className="relative md:col-span-2">
            <Search
              size={17}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search businesses, categories..."
              className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Stage */}
          <div className="relative">
            <Filter
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />

            <select
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              className="w-full appearance-none border rounded-lg pl-9 pr-8 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">All stages</option>

              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, ' ')}
                </option>
              ))}
            </select>

            <ChevronDown
              size={15}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
          </div>

          {/* Campaign */}
          <div className="relative">
            <select
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              className="w-full appearance-none border rounded-lg px-3 pr-8 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">All campaigns</option>

              {campaigns.map((campaign) => (
                <option key={campaign.id} value={campaign.id}>
                  {campaign.natural_language_input.slice(0, 45)}
                </option>
              ))}
            </select>

            <ChevronDown
              size={15}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
          </div>
        </div>
      </div>

      {/* Empty */}
      {filteredLeads.length === 0 ? (
        <div className="bg-white border rounded-xl p-12 text-center">
          <Users
            size={36}
            className="mx-auto text-slate-300 mb-3"
          />

          <h2 className="font-semibold text-slate-800 mb-1">
            {leads.length === 0
              ? 'No leads yet'
              : 'No matching leads'}
          </h2>

          <p className="text-sm text-slate-500">
            {leads.length === 0
              ? 'Run a campaign to discover qualified prospects.'
              : 'Try changing your search or filters.'}
          </p>
        </div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          {/* Desktop table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b">
                <tr className="text-left text-slate-500">
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
                    Campaign
                  </th>

                  <th className="px-4 py-3 font-medium text-right">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredLeads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="border-t hover:bg-slate-50 transition"
                  >
                    {/* Business */}
                    <td className="px-4 py-3">
                      <Link
                        to={`/leads/${lead.id}`}
                        className="font-medium text-slate-900 hover:text-brand-700"
                      >
                        {lead.business_name ||
                          lead.business_id.slice(0, 12)}
                      </Link>

                      <p className="text-xs text-slate-400 mt-0.5">
                        {lead.business_id.slice(0, 12)}
                      </p>
                    </td>

                    {/* Score */}
                    <td className="px-4 py-3">
                      {lead.opportunity_score != null ? (
                        <span className="font-semibold">
                          {Math.round(lead.opportunity_score)}
                        </span>
                      ) : (
                        <span className="text-slate-400">
                          —
                        </span>
                      )}
                    </td>

                    {/* Stage */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 rounded-md text-xs font-medium capitalize ${stageClass(
                          lead.stage || 'new',
                        )}`}
                      >
                        {(lead.stage || 'new').replace(
                          /_/g,
                          ' ',
                        )}
                      </span>
                    </td>

                    {/* Category */}
                    <td className="px-4 py-3 text-slate-600">
                      {lead.business_category || '—'}
                    </td>

                    {/* Campaign */}
                    <td className="px-4 py-3 text-slate-500 max-w-[220px]">
                      <span className="truncate block">
                        {getCampaignName(lead.campaign_id)}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/leads/${lead.id}`}
                        className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700 text-xs font-medium"
                      >
                        View
                        <ExternalLink size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="border-t px-4 py-3 text-xs text-slate-500 flex justify-between">
            <span>
              Showing {filteredLeads.length} lead
              {filteredLeads.length !== 1 ? 's' : ''}
            </span>

            <span>
              {campaigns.length} campaign
              {campaigns.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}