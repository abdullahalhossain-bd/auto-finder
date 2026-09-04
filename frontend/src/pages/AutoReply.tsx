import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, MessageSquare, Shield, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { PageHeader } from '../components/ui'
import { PaidLock, useQuota } from '../components/QuotaBar'

export default function AutoReply() {
  const { quota } = useQuota()
  const isPaid = Boolean(quota?.is_paid || quota?.features?.ai_auto_reply)

  const [enabled, setEnabled] = useState(false)
  const [approvalMode, setApprovalMode] = useState(true)
  const [tone, setTone] = useState('professional')
  const [language, setLanguage] = useState('en')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // Local preference only until backend automation settings exist
    try {
      const raw = localStorage.getItem('auto_reply_settings')
      if (raw) {
        const s = JSON.parse(raw)
        setEnabled(Boolean(s.enabled))
        setApprovalMode(s.approvalMode !== false)
        setTone(s.tone || 'professional')
        setLanguage(s.language || 'en')
      }
    } catch {
      /* ignore */
    }
  }, [])

  const save = () => {
    localStorage.setItem(
      'auto_reply_settings',
      JSON.stringify({ enabled, approvalMode, tone, language })
    )
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (quota && !isPaid) {
    return (
      <div className="space-y-6 max-w-2xl">
        <PageHeader
          title="AI Auto Reply"
          description="Detect intent and draft replies — paid plans only."
        />
        <PaidLock
          feature="ai_auto_reply"
          title="AI Auto Reply is a paid feature"
          description="Upgrade to enable intent detection, AI reply drafts, and human-approval mode for inbound messages."
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title="AI Auto Reply"
        description="Intent detection + AI drafts. Sending still respects approval and ESP rules."
      />

      <div className="bg-white border rounded-2xl p-5 space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 flex items-center justify-center">
              <Bot size={20} />
            </div>
            <div>
              <p className="font-semibold text-slate-900">AI Auto Reply</p>
              <p className="text-sm text-slate-500">
                {enabled ? 'ON — drafts will appear in Inbox' : 'OFF'}
              </p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            onClick={() => setEnabled((v) => !v)}
            className={`relative w-12 h-7 rounded-full transition ${
              enabled ? 'bg-brand-600' : 'bg-slate-300'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white shadow transition ${
                enabled ? 'translate-x-5' : ''
              }`}
            />
          </button>
        </div>

        <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={approvalMode}
            onChange={(e) => setApprovalMode(e.target.checked)}
            className="mt-1 rounded border-slate-300 text-brand-600"
          />
          <div>
            <p className="text-sm font-medium text-slate-800 flex items-center gap-1.5">
              <Shield size={14} /> Human approval mode
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              Recommended. AI never sends without an explicit approve (same as outreach
              safety rules).
            </p>
          </div>
        </label>

        <div className="grid sm:grid-cols-2 gap-4">
          <label className="text-sm block">
            <span className="font-medium text-slate-700 mb-1.5 block">Tone</span>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="w-full border rounded-lg px-3 py-2.5 text-sm"
            >
              <option value="professional">Professional</option>
              <option value="friendly">Friendly</option>
              <option value="concise">Concise</option>
            </select>
          </label>
          <label className="text-sm block">
            <span className="font-medium text-slate-700 mb-1.5 block">Language</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full border rounded-lg px-3 py-2.5 text-sm"
            >
              <option value="en">English</option>
              <option value="bn">Bangla</option>
              <option value="hi">Hindi</option>
            </select>
          </label>
        </div>

        <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-sm text-slate-600 space-y-2">
          <p className="font-medium text-slate-800 flex items-center gap-1.5">
            <MessageSquare size={14} /> Supported intents
          </p>
          <ul className="list-disc pl-5 text-xs space-y-1">
            <li>Interested / ask for more info</li>
            <li>Not now / follow up later</li>
            <li>Unsubscribe / do not contact</li>
            <li>Wrong person / not a fit</li>
          </ul>
          <p className="text-xs text-slate-500">
            Replies flow through authorized ESP webhooks only — no unauthorized scraping.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={save}
            className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700"
          >
            <Sparkles size={16} />
            Save settings
          </button>
          {saved && <span className="text-sm text-emerald-600">Saved</span>}
          <Link to="/inbox" className="text-sm text-brand-600 hover:underline">
            Open Inbox
          </Link>
        </div>
      </div>
    </div>
  )
}
