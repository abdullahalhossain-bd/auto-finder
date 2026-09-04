import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import {
  Mail,
  Search,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
} from 'lucide-react'

type Message = {
  id: string
  lead_id: string
  subject?: string
  content: string
  status: string
  to_email?: string
  created_at?: string
  updated_at?: string
}

const STATUS_OPTIONS = [
  'all',
  'pending',
  'approved',
  'sent',
  'rejected',
  'failed',
  'replied',
]

export default function Outreach() {
  const [messages, setMessages] = useState<Message[]>([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')

    try {
      /*
       * Existing API exposes pending messages and replies.
       * We combine them here so the frontend has a central
       * outreach activity view.
       */
      const [pending, replies] = await Promise.all([
        api.listPendingMessages(),
        api.listReplies(),
      ])

      const merged = [...pending, ...replies] as Message[]

      // Remove duplicate messages by ID
      const unique = Array.from(
        new Map(merged.map((m) => [m.id, m])).values(),
      )

      setMessages(unique)
    } catch (e: any) {
      setError(e.message || 'Failed to load outreach')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()

    return messages
      .filter((m) => {
        const matchesSearch =
          !q ||
          m.content?.toLowerCase().includes(q) ||
          m.subject?.toLowerCase().includes(q) ||
          m.to_email?.toLowerCase().includes(q) ||
          m.lead_id?.toLowerCase().includes(q)

        const matchesStatus =
          status === 'all' ||
          m.status?.toLowerCase() === status

        return matchesSearch && matchesStatus
      })
      .sort((a, b) => {
        const da = new Date(
          a.updated_at || a.created_at || 0,
        ).getTime()

        const db = new Date(
          b.updated_at || b.created_at || 0,
        ).getTime()

        return db - da
      })
  }, [messages, search, status])

  const stats = useMemo(() => {
    return {
      total: messages.length,
      pending: messages.filter(
        (m) => m.status === 'pending',
      ).length,
      sent: messages.filter(
        (m) => m.status === 'sent',
      ).length,
      replied: messages.filter(
        (m) => m.status === 'replied',
      ).length,
      failed: messages.filter(
        (m) => m.status === 'failed',
      ).length,
    }
  }, [messages])

  const statusStyle = (value: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-blue-100 text-blue-700',
      sent: 'bg-green-100 text-green-700',
      replied: 'bg-purple-100 text-purple-700',
      rejected: 'bg-slate-100 text-slate-600',
      failed: 'bg-red-100 text-red-700',
    }

    return styles[value] || 'bg-slate-100 text-slate-600'
  }

  const StatusIcon = ({ value }: { value: string }) => {
    if (value === 'sent' || value === 'replied') {
      return <CheckCircle2 size={14} />
    }

    if (value === 'failed') {
      return <XCircle size={14} />
    }

    if (value === 'pending') {
      return <Clock size={14} />
    }

    return <AlertCircle size={14} />
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-40 bg-slate-100 rounded animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[1, 2, 3, 4, 5].map((x) => (
            <div
              key={x}
              className="h-24 bg-slate-100 rounded-xl animate-pulse"
            />
          ))}
        </div>
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Outreach
          </h1>

          <p className="text-sm text-slate-500 mt-1">
            Track message drafts, approvals, sends and replies.
          </p>
        </div>

        <Link
          to="/approvals"
          className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700"
        >
          <Mail size={16} />
          Approval Queue
        </Link>
      </div>

      {error && (
        <div className="mb-5 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
          <AlertCircle size={17} />
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <Stat
          icon={<Mail size={17} />}
          label="Total"
          value={stats.total}
        />

        <Stat
          icon={<Clock size={17} />}
          label="Pending"
          value={stats.pending}
        />

        <Stat
          icon={<CheckCircle2 size={17} />}
          label="Sent"
          value={stats.sent}
        />

        <Stat
          icon={<Mail size={17} />}
          label="Replied"
          value={stats.replied}
        />

        <Stat
          icon={<XCircle size={17} />}
          label="Failed"
          value={stats.failed}
        />
      </div>

      {/* Filters */}
      <div className="bg-white border rounded-xl p-4 mb-5">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search
              size={17}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search messages, email addresses..."
              className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm bg-white"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s === 'all'
                  ? 'All statuses'
                  : s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={load}
            className="border rounded-lg px-4 py-2 text-sm hover:bg-slate-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Messages */}
      {filtered.length === 0 ? (
        <div className="bg-white border rounded-xl p-12 text-center">
          <Mail
            size={38}
            className="mx-auto text-slate-300 mb-3"
          />

          <h2 className="font-semibold text-slate-800 mb-1">
            No outreach messages
          </h2>

          <p className="text-sm text-slate-500">
            Generate a message from a lead or start a campaign.
          </p>
        </div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b">
                <tr className="text-left text-slate-500">
                  <th className="px-4 py-3 font-medium">
                    Recipient
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Subject
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Status
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Message
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Updated
                  </th>

                  <th className="px-4 py-3 text-right font-medium">
                    Lead
                  </th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((message) => (
                  <tr
                    key={message.id}
                    className="border-t hover:bg-slate-50"
                  >
                    {/* Recipient */}
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">
                        {message.to_email || 'Unknown recipient'}
                      </div>

                      <div className="text-xs text-slate-400 mt-0.5">
                        {message.id.slice(0, 8)}
                      </div>
                    </td>

                    {/* Subject */}
                    <td className="px-4 py-3 max-w-[220px]">
                      <span className="truncate block">
                        {message.subject || 'No subject'}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium capitalize ${statusStyle(
                          message.status,
                        )}`}
                      >
                        <StatusIcon value={message.status} />
                        {message.status}
                      </span>
                    </td>

                    {/* Preview */}
                    <td className="px-4 py-3 max-w-[300px]">
                      <span className="block truncate text-slate-500">
                        {message.content}
                      </span>
                    </td>

                    {/* Date */}
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                      {message.updated_at ||
                      message.created_at ? (
                        new Date(
                          message.updated_at ||
                            message.created_at ||
                            '',
                        ).toLocaleDateString()
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Lead */}
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/leads/${message.lead_id}`}
                        className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700 text-xs font-medium"
                      >
                        Open
                        <ExternalLink size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="border-t px-4 py-3 text-xs text-slate-500">
            Showing {filtered.length} of {messages.length} messages
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: number
}) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
        {icon}
        {label}
      </div>

      <p className="text-2xl font-bold text-slate-900">
        {value}
      </p>
    </div>
  )
}