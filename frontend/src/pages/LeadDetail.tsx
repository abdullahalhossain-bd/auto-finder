import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Check,
  Clock,
  ExternalLink,
  Globe,
  Mail,
  MapPin,
  MessageSquare,
  Phone,
  Sparkles,
  UserX,
} from 'lucide-react'
import { PageSkeleton, CardListSkeleton, EmptyState, ErrorBanner } from '../components/ui'

import { api } from '../lib/api'
import { Lead } from '../types'

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

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>()

  const [lead, setLead] = useState<Lead | null>(null)

  const [message, setMessage] = useState('')
  const [subject, setSubject] = useState('')
  const [rationale, setRationale] = useState('')
  const [provider, setProvider] = useState('')

  const [serviceOffered, setServiceOffered] =
    useState('websites and online booking')

  const [loading, setLoading] = useState(true)
  const [stageSaving, setStageSaving] = useState(false)
  const [savingMessage, setSavingMessage] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [followupLoading, setFollowupLoading] =
    useState(false)

  const [msgStatus, setMsgStatus] = useState('')
  const [error, setError] = useState('')

  const [createdMessageId, setCreatedMessageId] =
    useState('')

  const [followupScheduled, setFollowupScheduled] =
    useState(false)

  const [dncOpen, setDncOpen] = useState(false)
  const [dncReason, setDncReason] = useState('')

  // ============================================================
  // LOAD LEAD
  // ============================================================

  const loadLead = async () => {
    if (!id) return

    try {
      setLoading(true)
      const data = await api.getLead(id)
      setLead(data)
    } catch (e: any) {
      setError(e.message || 'Failed to load lead')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLead()
  }, [id])

  // ============================================================
  // STAGE
  // ============================================================

  const updateStage = async (
    stage: string
  ) => {
    if (!id) return

    try {
      setStageSaving(true)
      setError('')

      const updated =
        await api.updateLead(id, {
          stage,
        })

      setLead(updated)
    } catch (e: any) {
      setError(
        e.message || 'Failed to update stage'
      )
    } finally {
      setStageSaving(false)
    }
  }

  // ============================================================
  // AI GENERATION
  // ============================================================

  const generateWithAI = async () => {
    if (!id) return

    try {
      setGenerating(true)
      setMsgStatus('')
      setError('')

      setRationale('')
      setProvider('')
      setSubject('')
      setMessage('')

      const result =
        await api.generateMessage(id, {
          service_offered:
            serviceOffered.trim() || undefined,
          async_mode: false,
        })

      if (
        result.content &&
        result.content.trim()
      ) {
        setMessage(result.content)

        setSubject(
          result.subject || ''
        )

        setRationale(
          result.ai_rationale || ''
        )

        setProvider(
          result.generation_provider || ''
        )

        if (
          result.generation_provider ===
          'template'
        ) {
          setMsgStatus(
            'Template draft ready. Review it before sending.'
          )
        } else {
          setMsgStatus(
            'AI draft ready. Review and send it to the Approval Queue.'
          )
        }

        return
      }

      if (result.status === 'queued') {
        setMsgStatus(
          'Generation queued. Check again shortly.'
        )
        return
      }

      setMsgStatus(
        'AI did not return a message.'
      )
    } catch (e: any) {
      setError(
        e.message || 'AI generation failed'
      )
    } finally {
      setGenerating(false)
    }
  }

  // ============================================================
  // CREATE MESSAGE
  // ============================================================

  const createMessage = async () => {
    if (!id || !message.trim()) {
      return
    }

    try {
      setSavingMessage(true)
      setMsgStatus('')
      setError('')

      const created =
        await api.createMessage(
          id,
          message.trim()
        )

      /*
       * IMPORTANT:
       * Automatically save returned message ID.
       * User no longer needs to paste UUID manually.
       */
      if (created?.id) {
        setCreatedMessageId(
          created.id
        )
      }

      setMsgStatus(
        'Message created and sent to the Approval Queue.'
      )

      setFollowupScheduled(false)
    } catch (e: any) {
      setError(
        e.message ||
          'Failed to create message'
      )
    } finally {
      setSavingMessage(false)
    }
  }

  // ============================================================
  // FOLLOW-UP
  // ============================================================

  const scheduleFollowup = async () => {
    if (!createdMessageId) {
      setError(
        'Create a message first before scheduling a follow-up.'
      )
      return
    }

    try {
      setFollowupLoading(true)
      setError('')

      await api.scheduleFollowup(
        createdMessageId,
        3
      )

      setFollowupScheduled(true)

      setMsgStatus(
        'Follow-up scheduled for 3 days later.'
      )
    } catch (e: any) {
      setError(
        e.message ||
          'Failed to schedule follow-up'
      )
    } finally {
      setFollowupLoading(false)
    }
  }

  // ============================================================
  // DO NOT CONTACT
  // ============================================================

  const confirmDnc = async () => {
    if (!id) return

    try {
      setError('')

      const updated =
        await api.doNotContact(
          id,
          dncReason.trim() ||
            'do_not_contact'
        )

      setLead(updated)
      setDncOpen(false)
      setDncReason('')

      setMsgStatus(
        'Lead marked as Do Not Contact.'
      )
    } catch (e: any) {
      setError(
        e.message ||
          'Failed to mark lead as Do Not Contact'
      )
    }
  }

  // ============================================================
  // STATES
  // ============================================================

  if (loading) {
    return <PageSkeleton />
  }

  if (!lead) {
    return (
      <div className="text-red-600">
        Lead not found
      </div>
    )
  }

  const contact =
    lead as Lead & {
      email?: string
      phone?: string
      website_url?: string
      address?: string
      latitude?: number
      longitude?: number
    }

  const score =
    lead.opportunity_score != null
      ? Math.round(
          lead.opportunity_score
        )
      : null

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="max-w-5xl">

      {/* Back */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mb-5 text-sm">
        <Link
          to={`/campaigns/${lead.campaign_id}`}
          className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700"
        >
          <ArrowLeft size={16} />
          Back to campaign
        </Link>
        <Link
          to="/leads"
          className="text-slate-500 hover:text-slate-700"
        >
          All leads
        </Link>
        <Link
          to={`/leads/${lead.id}/intelligence`}
          className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700 font-medium"
        >
          <Sparkles size={14} />
          Intelligence view
        </Link>
      </div>

      {/* Header */}
      <div className="bg-white border rounded-xl p-5 mb-5">
        <div className="flex items-start justify-between gap-4">

          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {lead.business_name ||
                'Unnamed Lead'}
            </h1>

            <p className="text-sm text-slate-500 mt-1">
              {lead.business_category ||
                'Business'}
            </p>
          </div>

          <button
            type="button"
            onClick={() =>
              setDncOpen(true)
            }
            disabled={
              lead.stage ===
              'do_not_contact'
            }
            className="inline-flex items-center gap-2 text-xs border border-red-200 text-red-700 px-3 py-2 rounded-lg hover:bg-red-50 disabled:opacity-50"
          >
            <UserX size={14} />
            {lead.stage ===
            'do_not_contact'
              ? 'Do Not Contact'
              : 'Do not contact'}
          </button>
        </div>

        {/* Contact info */}
        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">

          {contact.email && (
            <a
              href={`mailto:${contact.email}`}
              className="flex items-center gap-2 text-sm text-slate-600 hover:text-brand-600"
            >
              <Mail size={16} />
              {contact.email}
            </a>
          )}

          {contact.phone && (
            <a
              href={`tel:${contact.phone}`}
              className="flex items-center gap-2 text-sm text-slate-600 hover:text-brand-600"
            >
              <Phone size={16} />
              {contact.phone}
            </a>
          )}

          {contact.website_url && (
            <a
              href={
                contact.website_url.startsWith(
                  'http'
                )
                  ? contact.website_url
                  : `https://${contact.website_url}`
              }
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 text-sm text-brand-600 hover:underline"
            >
              <Globe size={16} />
              Website
              <ExternalLink size={13} />
            </a>
          )}

          {contact.address && (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <MapPin size={16} />
              {contact.address}
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-5 p-3 bg-red-50 border border-red-100 text-red-700 text-sm rounded-lg">
          {error}
        </div>
      )}

      {/* Success */}
      {msgStatus && (
        <div className="mb-5 p-3 bg-green-50 border border-green-100 text-green-700 text-sm rounded-lg flex items-center gap-2">
          <Check size={16} />
          {msgStatus}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">

        <div className="bg-white border rounded-xl p-4">
          <p className="text-xs text-slate-500 mb-1">
            Opportunity Score
          </p>

          <p className="text-3xl font-bold">
            {score ?? '—'}
          </p>
        </div>

        <div className="bg-white border rounded-xl p-4">
          <p className="text-xs text-slate-500 mb-1">
            Pipeline Stage
          </p>

          <select
            value={lead.stage}
            onChange={(e) =>
              updateStage(
                e.target.value
              )
            }
            disabled={stageSaving}
            className="border rounded-lg px-3 py-2 text-sm w-full"
          >
            {STAGES.map(
              (stage) => (
                <option
                  key={stage}
                  value={stage}
                >
                  {stage.replace(
                    /_/g,
                    ' '
                  )}
                </option>
              )
            )}
          </select>
        </div>

        <div className="bg-white border rounded-xl p-4">
          <p className="text-xs text-slate-500 mb-1">
            Category
          </p>

          <p className="font-semibold capitalize">
            {lead.business_category ||
              '—'}
          </p>
        </div>
      </div>

      {/* Confidence */}
      {lead.confidence_summary && (
        <div className="bg-slate-50 border rounded-xl p-4 mb-5">
          <p className="font-medium mb-3">
            Data Confidence
          </p>

          <div className="flex flex-wrap gap-2">
            {Object.entries(
              lead.confidence_summary
            ).map(([key, value]) => (
              <span
                key={key}
                className="px-3 py-1.5 bg-white border rounded-lg text-xs"
              >
                {key.replace(
                  /_/g,
                  ' '
                )}
                :{' '}
                <strong>
                  {String(value)}
                </strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Score */}
      {lead.score_breakdown && (
        <div className="bg-white border rounded-xl p-4 mb-5">
          <p className="font-medium mb-3">
            Opportunity Score Breakdown
          </p>

          <div className="bg-slate-50 rounded-lg p-3 overflow-auto">
            <pre className="text-xs text-slate-600 whitespace-pre-wrap">
              {JSON.stringify(
                lead.score_breakdown,
                null,
                2
              )}
            </pre>
          </div>
        </div>
      )}

      {/* Outreach */}
      <div className="bg-white border rounded-xl p-5">

        <div className="flex items-center gap-2 mb-1">
          <MessageSquare
            size={18}
            className="text-brand-600"
          />

          <h2 className="text-lg font-semibold">
            Create Outreach Message
          </h2>
        </div>

        <p className="text-xs text-slate-500 mb-5">
          AI uses verified lead facts.
          Nothing is sent automatically.
          Every message must be reviewed
          and approved.
        </p>

        {/* Service */}
        <label className="block text-xs font-medium text-slate-600 mb-1">
          What are you offering?
        </label>

        <input
          value={serviceOffered}
          onChange={(e) =>
            setServiceOffered(
              e.target.value
            )
          }
          className="w-full border rounded-lg px-3 py-2.5 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="e.g. website redesign, online booking setup"
        />

        {/* Generate */}
        <div className="mb-5">
          <button
            type="button"
            onClick={generateWithAI}
            disabled={
              generating ||
              savingMessage
            }
            className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            <Sparkles size={16} />

            {generating
              ? 'Generating...'
              : 'Generate with AI'}
          </button>

          {provider && (
            <span className="ml-3 text-xs text-slate-500">
              Generated via{' '}
              <strong>
                {provider}
              </strong>
            </span>
          )}
        </div>

        {/* AI rationale */}
        {rationale && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-100 rounded-lg text-xs text-amber-900">
            <strong>
              AI rationale:
            </strong>{' '}
            {rationale}
          </div>
        )}

        {/* Subject */}
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Subject
        </label>

        <input
          value={subject}
          onChange={(e) =>
            setSubject(
              e.target.value
            )
          }
          className="w-full border rounded-lg px-3 py-2.5 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="Email subject"
        />

        {/* Body */}
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Message
        </label>

        <textarea
          value={message}
          onChange={(e) =>
            setMessage(
              e.target.value
            )
          }
          rows={8}
          placeholder="Generate with AI, or write your own message..."
          className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
        />

        {/* Actions */}
        <div className="mt-4 flex flex-wrap items-center gap-3">

          <button
            type="button"
            onClick={createMessage}
            disabled={
              savingMessage ||
              generating ||
              !message.trim()
            }
            className="bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {savingMessage
              ? 'Sending...'
              : 'Send to Approval Queue'}
          </button>

          {createdMessageId && (
            <span className="text-xs text-slate-500">
              Message created ✓
            </span>
          )}
        </div>

        {/* Follow-up */}
        <div className="mt-6 pt-5 border-t">

          <div className="flex items-center gap-2 mb-1">
            <Clock size={16} />

            <p className="font-medium text-sm">
              Follow-up
            </p>
          </div>

          <p className="text-xs text-slate-500 mb-3">
            Schedule one follow-up 3 days
            after the message.
          </p>

          <button
            type="button"
            onClick={
              scheduleFollowup
            }
            disabled={
              !createdMessageId ||
              followupLoading ||
              followupScheduled
            }
            className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50"
          >
            {followupScheduled
              ? 'Follow-up Scheduled ✓'
              : followupLoading
                ? 'Scheduling...'
                : 'Schedule 3-Day Follow-up'}
          </button>

          {!createdMessageId && (
            <p className="text-xs text-slate-400 mt-2">
              Create a message first.
            </p>
          )}
        </div>
      </div>

      {/* DNC modal */}
      {dncOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">

          <div className="bg-white rounded-xl p-5 max-w-md w-full shadow-xl">

            <div className="flex items-center gap-2 mb-2">
              <UserX
                size={20}
                className="text-red-600"
              />

              <h3 className="font-semibold text-lg">
                Mark Do Not Contact?
              </h3>
            </div>

            <p className="text-sm text-slate-600 mb-4">
              This lead will be added to the
              suppression list and should not
              receive outreach.
            </p>

            <input
              className="w-full border rounded-lg px-3 py-2.5 text-sm mb-4"
              placeholder="Reason (optional)"
              value={dncReason}
              onChange={(e) =>
                setDncReason(
                  e.target.value
                )
              }
            />

            <div className="flex justify-end gap-2">

              <button
                type="button"
                className="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50"
                onClick={() =>
                  setDncOpen(false)
                }
              >
                Cancel
              </button>

              <button
                type="button"
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
                onClick={
                  confirmDnc
                }
              >
                Confirm
              </button>

            </div>
          </div>
        </div>
      )}
    </div>
  )
}