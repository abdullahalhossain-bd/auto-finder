import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Message } from '../types'
import {
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Mail,
} from 'lucide-react'
import { CardListSkeleton, EmptyState, ErrorBanner, useToast } from '../components/ui'

type SendingIdentity = {
  can_send?: boolean
  configured?: boolean
  sending_paused?: boolean
  pause_reason?: string
  from_address?: string
  from_name?: string
  verified_domain?: string
  spf_verified?: boolean
  dkim_verified?: boolean
}

export default function Approvals() {
  const { success: toastSuccess, error: toastError } = useToast()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [acting, setActing] = useState<string | null>(null)

  const [canSend, setCanSend] = useState<boolean | null>(null)
  const [identity, setIdentity] = useState<SendingIdentity | null>(null)

  const [error, setError] = useState('')

  const load = async (showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    setError('')

    try {
      const [msgs, sendingIdentity] = await Promise.all([
        api.listPendingMessages(),
        api
          .getSendingIdentity()
          .catch(
            () =>
              ({
                can_send: false,
                configured: false,
              }) as SendingIdentity,
          ),
      ])

      setMessages(msgs || [])

      const id = sendingIdentity as SendingIdentity

      setIdentity(id)
      setCanSend(Boolean(id?.can_send))
    } catch (e: unknown) {
      setError(
        (e as Error).message || 'Failed to load approval queue.',
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const approve = async (id: string) => {
    if (!canSend) {
      setError(
        'Sending identity is not verified. Verify SPF and DKIM in Settings first.',
      )
      return
    }

    const confirmed = window.confirm(
      'Approve this message for sending?\n\nThis action will queue the message for delivery.',
    )

    if (!confirmed) return

    setActing(id)
    setError('')

    try {
      await api.approveMessage(id)

      setMessages((prev) => prev.filter((m) => m.id !== id))

      toastSuccess('Message approved and queued for sending.')
    } catch (e: unknown) {
      const msg = (e as Error).message || 'Failed to approve message.'
      setError(msg)
      toastError(msg)
    } finally {
      setActing(null)
    }
  }

  const reject = async (id: string) => {
    const confirmed = window.confirm(
      'Reject this message?\n\nThe message will be removed from the approval queue.',
    )

    if (!confirmed) return

    setActing(id)
    setError('')

    try {
      await api.rejectMessage(id)

      setMessages((prev) => prev.filter((m) => m.id !== id))

      toastSuccess('Message rejected.')
    } catch (e: unknown) {
      const msg = (e as Error).message || 'Failed to reject message.'
      setError(msg)
      toastError(msg)
    } finally {
      setActing(null)
    }
  }

  if (loading) {
    return <CardListSkeleton count={3} />
  }

  const identityBlocked =
    canSend === false ||
    identity?.sending_paused === true

  return (
    <div className="max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Approval Queue
          </h1>

          <p className="text-slate-500 text-sm mt-1">
            Review every AI-generated message before it is sent.
          </p>
        </div>

        <button
          type="button"
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-2 border px-3 py-2 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw
            size={15}
            className={refreshing ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {/* Safety notice */}
      <div className="mb-6 bg-slate-50 border rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Mail
            size={18}
            className="text-slate-500 mt-0.5 flex-shrink-0"
          />

          <div className="text-sm">
            <p className="font-medium text-slate-800">
              Human approval required
            </p>

            <p className="text-slate-500 mt-1">
              Nothing is sent automatically from this queue. Review
              the recipient, subject and message content before
              approving.
            </p>
          </div>
        </div>
      </div>

      {/* Sending identity warning */}
      {identityBlocked && (
        <div className="mb-5 flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-xl p-4">
          <AlertTriangle
            size={19}
            className="mt-0.5 flex-shrink-0"
          />

          <div className="text-sm">
            <p className="font-semibold">
              Sending is currently unavailable
            </p>

            <p className="mt-1">
              {identity?.sending_paused
                ? identity.pause_reason ||
                  'Sending has been paused.'
                : 'Verify your sending identity before approving messages.'}
            </p>

            <div className="mt-2 flex flex-wrap gap-3">
              <Link
                to="/settings"
                className="underline font-medium"
              >
                Open Settings →
              </Link>

              {identity && (
                <span className="text-xs text-amber-800">
                  SPF {identity.spf_verified ? '✓' : '✗'} · DKIM{' '}
                  {identity.dkim_verified ? '✓' : '✗'}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <ErrorBanner
          message={error}
          onRetry={() => load()}
          onDismiss={() => setError('')}
        />
      )}

      {/* Success */}
      

      {/* Queue count */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">
          Pending messages
        </h2>

        <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
          {messages.length}{' '}
          {messages.length === 1 ? 'message' : 'messages'}
        </span>
      </div>

      {/* Empty */}
      {messages.length === 0 ? (
        <EmptyState
          icon={<Check size={28} className="text-green-600" />}
          title="Approval queue is clear"
          description="There are no messages waiting for approval. Generate outreach from a campaign to see items here."
          actionLabel="View Campaigns"
          actionTo="/campaigns"
        />
      ) : (
        <div className="space-y-4">
          {messages.map((m) => {
            const isActing = acting === m.id

            return (
              <div
                key={m.id}
                className="bg-white border rounded-xl overflow-hidden"
              >
                {/* Message header */}
                <div className="px-5 py-4 border-b bg-slate-50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-xs text-slate-500 mb-1">
                        Message #{m.id.slice(0, 8)}
                      </p>

                      {m.subject ? (
                        <h3 className="font-semibold text-slate-900 truncate">
                          {m.subject}
                        </h3>
                      ) : (
                        <h3 className="font-semibold text-slate-500">
                          No subject
                        </h3>
                      )}
                    </div>

                    <span className="flex-shrink-0 text-xs px-2.5 py-1 bg-yellow-100 text-yellow-700 rounded-full capitalize">
                      {m.status}
                    </span>
                  </div>
                </div>

                {/* Message body */}
                <div className="p-5">
                  {/* Recipient */}
                  {m.to_email && (
                    <div className="mb-4">
                      <p className="text-xs text-slate-500 mb-1">
                        Recipient
                      </p>

                      <p className="text-sm font-medium text-slate-800">
                        {m.to_email}
                      </p>
                    </div>
                  )}

                  {/* Subject */}
                  {m.subject && (
                    <div className="mb-4">
                      <p className="text-xs text-slate-500 mb-1">
                        Subject
                      </p>

                      <p className="text-sm text-slate-800">
                        {m.subject}
                      </p>
                    </div>
                  )}

                  {/* Body */}
                  <div>
                    <p className="text-xs text-slate-500 mb-1">
                      Message
                    </p>

                    <div className="bg-slate-50 border rounded-lg p-4 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
                      {m.content}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-5 flex items-center justify-between gap-3 flex-wrap">
                    <Link
                      to={`/leads/${m.lead_id}`}
                      className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 hover:underline"
                    >
                      View lead
                      <ExternalLink size={14} />
                    </Link>

                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => reject(m.id)}
                        disabled={isActing}
                        className="flex items-center gap-1.5 border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
                      >
                        <X size={16} />

                        {isActing
                          ? 'Processing…'
                          : 'Reject'}
                      </button>

                      <button
                        type="button"
                        onClick={() => approve(m.id)}
                        disabled={isActing || !canSend}
                        title={
                          !canSend
                            ? 'Verify sending identity first'
                            : 'Approve and queue for sending'
                        }
                        className="flex items-center gap-1.5 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                      >
                        <Check size={16} />

                        {isActing
                          ? 'Processing…'
                          : 'Approve & Send'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer safety note */}
      <div className="mt-6 text-xs text-slate-400">
        Approving a message authorizes it to enter the sending
        pipeline. Make sure the recipient, content and sending
        identity are correct before approval.
      </div>
    </div>
  )
}