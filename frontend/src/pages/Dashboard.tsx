import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { api } from '../lib/api'
import { Campaign } from '../types'
import {
  Megaphone,
  Users,
  CheckSquare,
  Plus,
  Search,
  RefreshCw,
  PlayCircle,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  TrendingUp,
} from 'lucide-react'
import { PageSkeleton, ErrorBanner, EmptyState } from '../components/ui'
import { WelcomeTour } from '../components/WelcomeTour'

export default function Dashboard() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [pendingCount, setPendingCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const loadDashboard = async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true)
    }

    try {
      setError('')
      const [campData, pending] = await Promise.all([
        api.listCampaigns(),
        api.listPendingMessages(),
      ])

      setCampaigns(campData.items || [])
      setPendingCount((pending || []).length)
    } catch (err: unknown) {
      console.error(err)
      setError((err as Error).message || 'Failed to load dashboard')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadDashboard()

    /*
     * Keep dashboard reasonably fresh.
     * Useful when Celery discovery is running.
     */
    const interval = setInterval(() => {
      loadDashboard()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <PageSkeleton rows={5} />
  }

  const totalLeads = campaigns.reduce(
    (sum, campaign) => sum + (campaign.qualified_leads || 0),
    0
  )

  const totalFound = campaigns.reduce(
    (sum, campaign) => sum + (campaign.total_leads_found || 0),
    0
  )

  const runningCampaigns = campaigns.filter(
    (c) =>
      c.status === 'running' ||
      c.status === 'processing'
  ).length

  const completedCampaigns = campaigns.filter(
    (c) =>
      c.status === 'completed' ||
      c.status === 'ready_for_review'
  ).length

  const failedCampaigns = campaigns.filter(
    (c) => c.status === 'failed'
  ).length

  const recentCampaigns = [...campaigns]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime()
    )
    .slice(0, 5)

  return (
    <div className="space-y-8">
      <WelcomeTour />
      {error && (
        <ErrorBanner
          message={error}
          onRetry={() => loadDashboard()}
          onDismiss={() => setError('')}
        />
      )}

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">

        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Dashboard
          </h1>

          <p className="text-sm text-slate-500 mt-1">
            Monitor campaigns, discovery and qualified leads.
          </p>
        </div>

        <div className="flex items-center gap-2">

          <button
            type="button"
            onClick={() => loadDashboard(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw
              size={16}
              className={refreshing ? 'animate-spin' : ''}
            />
            Refresh
          </button>

          <Link
            to="/campaigns/new"
            className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700"
          >
            <Plus size={16} />
            New Campaign
          </Link>

        </div>
      </div>


      {/* =====================================================
          MAIN STATS
      ===================================================== */}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

        <StatCard
          icon={<Megaphone size={19} />}
          label="Campaigns"
          value={campaigns.length}
          description="Total campaigns"
        />

        <StatCard
          icon={<Search size={19} />}
          label="Businesses Found"
          value={totalFound}
          description="Discovered businesses"
        />

        <StatCard
          icon={<Users size={19} />}
          label="Qualified Leads"
          value={totalLeads}
          description="Ready for outreach"
        />

        <StatCard
          icon={<CheckSquare size={19} />}
          label="Pending Approvals"
          value={pendingCount}
          description={
            pendingCount > 0
              ? 'Action required'
              : 'Nothing pending'
          }
          alert={pendingCount > 0}
        />

      </div>

      {/* =====================================================
          GROWTH TREND
      ===================================================== */}

      {campaigns.length > 0 && <GrowthTrend campaigns={campaigns} />}

      {/* =====================================================
          CAMPAIGN STATUS
      ===================================================== */}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        <MiniStatusCard
          icon={<PlayCircle size={18} />}
          label="Running"
          value={runningCampaigns}
          description="Currently discovering"
        />

        <MiniStatusCard
          icon={<CheckCircle2 size={18} />}
          label="Completed"
          value={completedCampaigns}
          description="Discovery completed"
        />

        <MiniStatusCard
          icon={<AlertCircle size={18} />}
          label="Failed"
          value={failedCampaigns}
          description="Need attention"
          danger={failedCampaigns > 0}
        />

      </div>


      {/* =====================================================
          QUICK ACTIONS
      ===================================================== */}

      <div>
        <h2 className="text-lg font-semibold mb-3">
          Quick Actions
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">

          <QuickAction
            to="/campaigns/new"
            icon={<Plus size={19} />}
            title="Create Campaign"
            description="Find new businesses"
          />

          <QuickAction
            to="/campaigns"
            icon={<Search size={19} />}
            title="View Campaigns"
            description="Manage your discovery campaigns"
          />

          <QuickAction
            to="/approvals"
            icon={<CheckSquare size={19} />}
            title="Review Approvals"
            description={
              pendingCount > 0
                ? `${pendingCount} message${pendingCount === 1 ? '' : 's'} waiting`
                : 'No pending approvals'
            }
          />

        </div>
      </div>


      {/* =====================================================
          RECENT CAMPAIGNS
      ===================================================== */}

      <div>

        <div className="flex items-center justify-between mb-3">

          <div>
            <h2 className="text-lg font-semibold">
              Recent Campaigns
            </h2>

            <p className="text-xs text-slate-500 mt-1">
              Your latest discovery campaigns.
            </p>
          </div>

          {campaigns.length > 0 && (
            <Link
              to="/campaigns"
              className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
            >
              View all
              <ArrowRight size={14} />
            </Link>
          )}

        </div>


        {recentCampaigns.length === 0 ? (
          <EmptyState
            icon={<Megaphone size={28} />}
            title="No campaigns yet"
            description="Create your first campaign to discover local businesses that need a website or booking system."
            actionLabel="Create Campaign"
            actionTo="/campaigns/new"
          />
        ) : (

          <div className="bg-white border rounded-xl overflow-hidden">

            <div className="overflow-x-auto">

              <table className="w-full text-sm">

                <thead className="bg-slate-50 text-slate-500 text-left">

                  <tr>

                    <th className="px-4 py-3 font-medium">
                      Campaign
                    </th>

                    <th className="px-4 py-3 font-medium">
                      Status
                    </th>

                    <th className="px-4 py-3 font-medium">
                      Found
                    </th>

                    <th className="px-4 py-3 font-medium">
                      Qualified
                    </th>

                    <th className="px-4 py-3 font-medium">
                      Created
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {recentCampaigns.map((campaign) => (

                    <tr
                      key={campaign.id}
                      className="border-t hover:bg-slate-50"
                    >

                      <td className="px-4 py-3 min-w-[280px]">

                        <Link
                          to={`/campaigns/${campaign.id}`}
                          className="text-brand-600 hover:underline font-medium"
                        >
                          {campaign.natural_language_input.slice(
                            0,
                            70
                          )}

                          {campaign.natural_language_input.length > 70
                            ? '…'
                            : ''}
                        </Link>

                      </td>


                      <td className="px-4 py-3">
                        <StatusBadge
                          status={campaign.status}
                        />
                      </td>


                      <td className="px-4 py-3">
                        {campaign.total_leads_found ?? 0}
                      </td>


                      <td className="px-4 py-3 font-medium">
                        {campaign.qualified_leads ?? 0}
                      </td>


                      <td className="px-4 py-3 text-slate-500">
                        {formatDate(campaign.created_at)}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          </div>

        )}

      </div>

    </div>
  )
}


/* ============================================================
   STAT CARD
   ============================================================ */

function StatCard({
  icon,
  label,
  value,
  description,
  alert = false,
}: {
  icon: React.ReactNode
  label: string
  value: number
  description: string
  alert?: boolean
}) {
  return (
    <div className="bg-white border rounded-xl p-5">

      <div className="flex items-center justify-between mb-3">

        <div className="flex items-center gap-2 text-slate-500 text-sm">
          {icon}
          {label}
        </div>

      </div>

      <p
        className={`text-3xl font-bold ${
          alert
            ? 'text-red-600'
            : 'text-slate-900'
        }`}
      >
        {value}
      </p>

      <p className="text-xs text-slate-500 mt-1">
        {description}
      </p>

    </div>
  )
}


/* ============================================================
   MINI STATUS CARD
   ============================================================ */

function MiniStatusCard({
  icon,
  label,
  value,
  description,
  danger = false,
}: {
  icon: React.ReactNode
  label: string
  value: number
  description: string
  danger?: boolean
}) {
  return (
    <div
      className={`bg-white border rounded-xl p-4 ${
        danger ? 'border-red-200' : ''
      }`}
    >

      <div className="flex items-center gap-2 text-slate-500 text-sm">
        {icon}
        {label}
      </div>

      <div className="flex items-end gap-2 mt-2">

        <p
          className={`text-2xl font-bold ${
            danger
              ? 'text-red-600'
              : 'text-slate-900'
          }`}
        >
          {value}
        </p>

      </div>

      <p className="text-xs text-slate-500 mt-1">
        {description}
      </p>

    </div>
  )
}


/* ============================================================
   QUICK ACTION
   ============================================================ */

function QuickAction({
  to,
  icon,
  title,
  description,
}: {
  to: string
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <Link
      to={to}
      className="bg-white border rounded-xl p-4 hover:border-brand-300 hover:shadow-sm transition"
    >

      <div className="flex items-center gap-3">

        <div className="w-9 h-9 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
          {icon}
        </div>

        <div className="min-w-0">

          <p className="font-medium text-slate-800">
            {title}
          </p>

          <p className="text-xs text-slate-500 mt-0.5">
            {description}
          </p>

        </div>

      </div>

    </Link>
  )
}


/* ============================================================
   STATUS BADGE
   ============================================================ */

function StatusBadge({
  status,
}: {
  status: string
}) {
  const normalized = status.toLowerCase()

  const styles: Record<string, string> = {
    draft:
      'bg-slate-100 text-slate-600',

    running:
      'bg-blue-100 text-blue-700',

    processing:
      'bg-blue-100 text-blue-700',

    completed:
      'bg-green-100 text-green-700',

    ready_for_review:
      'bg-green-100 text-green-700',

    paused:
      'bg-yellow-100 text-yellow-700',

    failed:
      'bg-red-100 text-red-700',
  }

  const className =
    styles[normalized] ||
    'bg-slate-100 text-slate-600'

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${className}`}
    >
      {status.replaceAll('_', ' ')}
    </span>
  )
}


/* ============================================================
   GROWTH TREND
   ============================================================ */

function GrowthTrend({ campaigns }: { campaigns: Campaign[] }) {
  // Derive a real per-day series from actual campaign data — no fake
  // numbers, just aggregated by the day each campaign was created.
  const byDay = new Map<string, { found: number; qualified: number }>()

  for (const c of campaigns) {
    const d = new Date(c.created_at)
    if (Number.isNaN(d.getTime())) continue
    const key = d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    })
    const entry = byDay.get(key) || { found: 0, qualified: 0 }
    entry.found += c.total_leads_found || 0
    entry.qualified += c.qualified_leads || 0
    byDay.set(key, entry)
  }

  const series = Array.from(byDay.entries())
    .map(([date, v]) => ({ date, ...v }))
    .slice(-14)

  if (series.length < 2) return null

  const totalQualified = series.reduce((s, r) => s + r.qualified, 0)

  return (
    <div className="bg-white border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-slate-900 flex items-center gap-2">
            <TrendingUp size={17} className="text-brand-600" />
            Discovery trend
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Businesses found vs. qualified leads, by campaign start date
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-slate-900">{totalQualified}</p>
          <p className="text-xs text-slate-400">qualified leads (14d)</p>
        </div>
      </div>
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer>
          <AreaChart data={series} margin={{ left: -20, right: 12, top: 4 }}>
            <defs>
              <linearGradient id="foundGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="qualifiedGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
            <Area
              type="monotone"
              dataKey="found"
              stroke="#94a3b8"
              fill="url(#foundGrad)"
              strokeWidth={2}
              name="Found"
            />
            <Area
              type="monotone"
              dataKey="qualified"
              stroke="#0ea5e9"
              fill="url(#qualifiedGrad)"
              strokeWidth={2}
              name="Qualified"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/* ============================================================
   DATE
   ============================================================ */

function formatDate(
  date: string
) {
  try {
    return new Date(date).toLocaleDateString(
      undefined,
      {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      }
    )
  } catch {
    return '—'
  }
}