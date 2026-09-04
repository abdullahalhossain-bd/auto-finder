import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Inbox as InboxIcon,
  RefreshCw,
  User,
  ExternalLink,
  Clock,
  Mail,
  AlertCircle,
} from 'lucide-react'
import { CardListSkeleton, EmptyState, ErrorBanner } from '../components/ui'
import { api } from '../lib/api'

type Msg = {
  id: string
  lead_id: string
  subject?: string
  content: string
  status: string
  to_email?: string
  updated_at?: string
}

function formatDate(value?: string) {
  if (!value) return 'Unknown date'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Unknown date'
  }

  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function statusClass(status: string) {
  const normalized = status.toLowerCase()

  if (normalized === 'replied' || normalized === 'received') {
    return 'bg-green-100 text-green-700'
  }

  if (normalized === 'pending') {
    return 'bg-yellow-100 text-yellow-700'
  }

  if (normalized === 'failed') {
    return 'bg-red-100 text-red-700'
  }

  return 'bg-slate-100 text-slate-600'
}

export default function Inbox() {
  const [items, setItems] = useState<Msg[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    setError('')

    try {
      const replies = await api.listReplies()
      setItems(replies)
    } catch (e: unknown) {
      const err = e as { message?: string }
      setError(err.message || 'Failed to load inbox')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const aTime = a.updated_at
        ? new Date(a.updated_at).getTime()
        : 0

      const bTime = b.updated_at
        ? new Date(b.updated_at).getTime()
        : 0

      return bTime - aTime
    })
  }, [items])

  if (loading) {
    return <CardListSkeleton count={3} />
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 flex items-center justify-center">
              <InboxIcon size={21} />
            </div>

            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                Inbox
              </h1>

              <p className="text-sm text-slate-500 mt-0.5">
                Replies from your outreach campaigns.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => load(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 border border-slate-200 bg-white px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw
            size={15}
            className={refreshing ? 'animate-spin' : ''}
          />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <div className="bg-white border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Mail size={15} />
            Total replies
          </div>

          <p className="text-2xl font-bold text-slate-900">
            {items.length}
          </p>
        </div>

        <div className="bg-white border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <User size={15} />
            Unique leads
          </div>

          <p className="text-2xl font-bold text-slate-900">
            {new Set(items.map((item) => item.lead_id)).size}
          </p>
        </div>

        <div className="bg-white border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Clock size={15} />
            Latest reply
          </div>

          <p className="text-sm font-medium text-slate-900 mt-2">
            {items[0]?.updated_at
              ? formatDate(items[0].updated_at)
              : '—'}
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <ErrorBanner
          message={error}
          onRetry={() => load()}
          onDismiss={() => setError('')}
        />
      )}

      {/* Empty state */}
      {!error && sortedItems.length === 0 && (
        <EmptyState
          icon={<InboxIcon size={28} />}
          title="No replies yet"
          description="When a prospect replies to one of your outreach messages, the conversation will appear here."
          actionLabel="View campaigns"
          actionTo="/campaigns"
        />
      )}

      {/* Replies */}
      {sortedItems.length > 0 && (
        <div className="space-y-3">
          {sortedItems.map((m) => (
            <div
              key={m.id}
              className="bg-white border rounded-xl p-4 sm:p-5 hover:border-slate-300 transition-colors"
            >
              {/* Top row */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-500 flex items-center justify-center shrink-0">
                    <User size={16} />
                  </div>

                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {m.to_email || 'Unknown contact'}
                    </p>

                    {m.updated_at && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        {formatDate(m.updated_at)}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex px-2 py-1 rounded-md text-xs font-medium capitalize ${statusClass(
                      m.status,
                    )}`}
                  >
                    {m.status.replace(/_/g, ' ')}
                  </span>

                  <Link
                    to={`/leads/${m.lead_id}`}
                    className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
                  >
                    Open lead
                    <ExternalLink size={12} />
                  </Link>
                </div>
              </div>

              {/* Subject */}
              {m.subject && (
                <div className="flex items-center gap-2 mb-2">
                  <Mail
                    size={14}
                    className="text-slate-400 shrink-0"
                  />

                  <p className="font-medium text-sm text-slate-900">
                    {m.subject}
                  </p>
                </div>
              )}

              {/* Message */}
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
                <p className="text-sm text-slate-700 whitespace-pre-wrap break-words leading-relaxed max-h-60 overflow-y-auto">
                  {m.content}
                </p>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
                <span>
                  Lead ID: {m.lead_id.slice(0, 8)}…
                </span>

                <Link
                  to={`/leads/${m.lead_id}`}
                  className="text-brand-600 hover:underline"
                >
                  View conversation
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}