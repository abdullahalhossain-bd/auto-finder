import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import {
  Building2,
  Users,
  Megaphone,
  Target,
  RefreshCw,
  Shield,
  Search,
} from 'lucide-react'
import { api } from '../lib/api'
import { PageHeader, ErrorBanner, PageSkeleton } from '../components/ui'

type Overview = {
  organizations: number
  organizations_active: number
  organizations_deleted: number
  users: number
  campaigns: number
  leads: number
  messages_sent: number
  plans: Record<string, number>
  demo_mode?: boolean
  note?: string
}

type OrgRow = {
  id: string
  name: string
  plan: string
  deleted_at?: string | null
  created_at?: string | null
  members: number
  campaigns: number
  leads: number
  subscription_status?: string | null
}

type UserRow = {
  id: string
  email: string
  created_at?: string | null
  memberships: number
  is_platform_admin?: boolean
}

export default function Admin() {
  const [allowed, setAllowed] = useState<boolean | null>(null)
  const [tab, setTab] = useState<'overview' | 'orgs' | 'users' | 'audit'>('overview')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [orgs, setOrgs] = useState<OrgRow[]>([])
  const [users, setUsers] = useState<UserRow[]>([])
  const [audit, setAudit] = useState<any[]>([])
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)

  const boot = useCallback(async () => {
    try {
      const me = await api.adminMe()
      setAllowed(Boolean(me.is_platform_admin))
      if (!me.is_platform_admin) {
        setLoading(false)
        return
      }
      const ov = await api.adminOverview()
      setOverview(ov)
    } catch (e: unknown) {
      setAllowed(false)
      setError((e as Error).message || 'Admin access denied')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    boot()
  }, [boot])

  const loadOrgs = async () => {
    setError('')
    try {
      const data = await api.adminListOrgs({ q: q || undefined })
      setOrgs(data.items || [])
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to load organizations')
    }
  }

  const loadUsers = async () => {
    setError('')
    try {
      const data = await api.adminListUsers({ q: q || undefined })
      setUsers(data.items || [])
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to load users')
    }
  }

  const loadAudit = async () => {
    setError('')
    try {
      const data = await api.adminAuditLogs()
      setAudit(data.items || [])
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to load audit logs')
    }
  }

  useEffect(() => {
    if (!allowed) return
    if (tab === 'orgs') loadOrgs()
    if (tab === 'users') loadUsers()
    if (tab === 'audit') loadAudit()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, allowed])

  const setPlan = async (id: string, plan: string) => {
    setBusyId(id)
    setError('')
    try {
      await api.adminPatchOrg(id, { plan })
      await loadOrgs()
      const ov = await api.adminOverview()
      setOverview(ov)
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to update plan')
    } finally {
      setBusyId(null)
    }
  }

  const toggleDelete = async (id: string, soft_delete: boolean) => {
    setBusyId(id)
    setError('')
    try {
      await api.adminPatchOrg(id, { soft_delete })
      await loadOrgs()
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to update org')
    } finally {
      setBusyId(null)
    }
  }

  if (loading) return <PageSkeleton />
  if (allowed === false) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Platform Admin"
        description="Cross-tenant operations. Restricted to PLATFORM_ADMIN_EMAILS."
        actions={
          <button
            type="button"
            onClick={() => boot()}
            className="inline-flex items-center gap-2 border px-3 py-2 rounded-lg text-sm hover:bg-slate-50"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        }
      />

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError('')} />
      )}

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {(
          [
            ['overview', 'Overview'],
            ['orgs', 'Organizations'],
            ['users', 'Users'],
            ['audit', 'Audit log'],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            onClick={() => setTab(k)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              tab === k
                ? 'bg-brand-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && overview && (
        <div className="space-y-4">
          {overview.demo_mode && (
            <div className="text-xs bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-3 py-2">
              {overview.note || 'DEMO DATA — simulated platform scale for buyer walkthrough.'}
            </div>
          )}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              {
                label: 'Organizations',
                value: overview.organizations_active,
                sub: `${overview.organizations_deleted} deleted`,
                icon: Building2,
              },
              { label: 'Users', value: overview.users, icon: Users },
              { label: 'Campaigns', value: overview.campaigns, icon: Megaphone },
              { label: 'Leads', value: overview.leads, icon: Target },
            ].map((c) => (
              <div
                key={c.label}
                className="bg-white border rounded-xl p-4"
              >
                <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                  <c.icon size={14} />
                  {c.label}
                </div>
                <p className="text-2xl font-bold text-slate-900">
                  {c.value.toLocaleString()}
                </p>
                {'sub' in c && c.sub && (
                  <p className="text-[11px] text-slate-400 mt-1">{c.sub}</p>
                )}
              </div>
            ))}
          </div>
          <div className="bg-white border rounded-xl p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Plan mix</h2>
            {Object.keys(overview.plans || {}).length > 0 ? (
              <div style={{ width: '100%', height: 180 }}>
                <ResponsiveContainer>
                  <BarChart
                    data={Object.entries(overview.plans).map(([plan, n]) => ({
                      plan: plan.charAt(0).toUpperCase() + plan.slice(1),
                      n,
                    }))}
                    layout="vertical"
                    margin={{ left: 8, right: 24 }}
                  >
                    <XAxis type="number" hide allowDecimals={false} />
                    <YAxis
                      type="category"
                      dataKey="plan"
                      tick={{ fontSize: 12, fill: '#475569' }}
                      axisLine={false}
                      tickLine={false}
                      width={70}
                    />
                    <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="n" radius={[0, 6, 6, 0]} fill="#0ea5e9" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No organizations yet.</p>
            )}
            <p className="text-xs text-slate-500 mt-2">
              Messages sent (all time):{' '}
              <strong>{overview.messages_sent.toLocaleString()}</strong>
            </p>
          </div>
        </div>
      )}

      {tab === 'orgs' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search org name…"
                className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm"
              />
            </div>
            <button
              type="button"
              onClick={loadOrgs}
              className="px-4 py-2 border rounded-lg text-sm hover:bg-slate-50"
            >
              Search
            </button>
          </div>
          <div className="bg-white border rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="px-3 py-2.5 font-medium">Organization</th>
                  <th className="px-3 py-2.5 font-medium">Plan</th>
                  <th className="px-3 py-2.5 font-medium">Members</th>
                  <th className="px-3 py-2.5 font-medium">Campaigns</th>
                  <th className="px-3 py-2.5 font-medium">Leads</th>
                  <th className="px-3 py-2.5 font-medium">Status</th>
                  <th className="px-3 py-2.5 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orgs.map((o) => (
                  <tr key={o.id} className="border-t">
                    <td className="px-3 py-2.5">
                      <p className="font-medium text-slate-900">{o.name}</p>
                      <p className="text-[11px] text-slate-400 font-mono">
                        {o.id.slice(0, 8)}…
                      </p>
                    </td>
                    <td className="px-3 py-2.5 capitalize">{o.plan}</td>
                    <td className="px-3 py-2.5">{o.members}</td>
                    <td className="px-3 py-2.5">{o.campaigns}</td>
                    <td className="px-3 py-2.5">{o.leads}</td>
                    <td className="px-3 py-2.5">
                      {o.deleted_at ? (
                        <span className="text-xs text-red-600">Deleted</span>
                      ) : (
                        <span className="text-xs text-emerald-700">
                          {o.subscription_status || 'active'}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {(['trial', 'starter', 'pro'] as const).map((p) => (
                          <button
                            key={p}
                            type="button"
                            disabled={busyId === o.id || o.plan === p}
                            onClick={() => setPlan(o.id, p)}
                            className="text-[11px] px-2 py-1 rounded border hover:bg-slate-50 disabled:opacity-40 capitalize"
                          >
                            {p}
                          </button>
                        ))}
                        <button
                          type="button"
                          disabled={busyId === o.id}
                          onClick={() =>
                            toggleDelete(o.id, !o.deleted_at)
                          }
                          className="text-[11px] px-2 py-1 rounded border border-red-200 text-red-700 hover:bg-red-50"
                        >
                          {o.deleted_at ? 'Restore' : 'Suspend'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {orgs.length === 0 && (
              <p className="p-6 text-sm text-slate-500 text-center">
                No organizations found.
              </p>
            )}
          </div>
        </div>
      )}

      {tab === 'users' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search email…"
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={loadUsers}
              className="px-4 py-2 border rounded-lg text-sm"
            >
              Search
            </button>
          </div>
          <div className="bg-white border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="px-3 py-2.5 font-medium">Email</th>
                  <th className="px-3 py-2.5 font-medium">Memberships</th>
                  <th className="px-3 py-2.5 font-medium">Created</th>
                  <th className="px-3 py-2.5 font-medium">Flags</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t">
                    <td className="px-3 py-2.5 font-medium">{u.email}</td>
                    <td className="px-3 py-2.5">{u.memberships}</td>
                    <td className="px-3 py-2.5 text-slate-500">
                      {u.created_at
                        ? new Date(u.created_at).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="px-3 py-2.5">
                      {u.is_platform_admin && (
                        <span className="inline-flex items-center gap-1 text-xs text-amber-800 bg-amber-50 px-2 py-0.5 rounded-full">
                          <Shield size={12} /> Platform admin
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'audit' && (
        <div className="bg-white border rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-3 py-2.5 font-medium">When</th>
                <th className="px-3 py-2.5 font-medium">Action</th>
                <th className="px-3 py-2.5 font-medium">Resource</th>
                <th className="px-3 py-2.5 font-medium">Org</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="px-3 py-2.5 text-slate-500 whitespace-nowrap">
                    {a.created_at
                      ? new Date(a.created_at).toLocaleString()
                      : '—'}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-xs">{a.action}</td>
                  <td className="px-3 py-2.5 text-xs">
                    {a.resource_type || '—'} {a.resource_id?.slice?.(0, 8) || ''}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-xs">
                    {a.organization_id?.slice?.(0, 8) || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {audit.length === 0 && (
            <p className="p-6 text-sm text-slate-500 text-center">No audit entries.</p>
          )}
        </div>
      )}

      <p className="text-xs text-slate-400">
        Admin access is controlled by server env{' '}
        <code className="bg-slate-100 px-1 rounded">PLATFORM_ADMIN_EMAILS</code>.
        Org owners manage their own team under Settings — this panel is platform-wide.
      </p>
    </div>
  )
}
