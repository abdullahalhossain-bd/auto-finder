import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import {
  CheckCircle2,
  XCircle,
  KeyRound,
  RefreshCw,
  Trash2,
  ExternalLink,
} from 'lucide-react'

type Credential = {
  id: string
  provider: string
  last4?: string
  label?: string
}

type Integration = {
  id: string
  name: string
  provider: string
  description: string
  category: string
  docs?: string
  configured: boolean
}

const INTEGRATIONS: Integration[] = [
  {
    id: 'google_places',
    name: 'Google Places',
    provider: 'google_places',
    description:
      'Discover local businesses, locations, categories and public business information.',
    category: 'Lead Discovery',
    docs: 'https://developers.google.com/maps/documentation/places/web-service',
    configured: false,
  },
  {
    id: 'groq',
    name: 'Groq AI',
    provider: 'groq',
    description:
      'Generate personalized outreach messages and AI-powered lead content.',
    category: 'AI',
    docs: 'https://console.groq.com/',
    configured: false,
  },
  {
    id: 'resend',
    name: 'Resend',
    provider: 'resend',
    description:
      'Send approved outreach emails through a transactional email provider.',
    category: 'Email',
    docs: 'https://resend.com/',
    configured: false,
  },
]

export default function Integrations() {
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<Integration | null>(null)
  const [provider, setProvider] = useState('')
  const [secret, setSecret] = useState('')
  const [label, setLabel] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')

    try {
      const data = await api.listApiCredentials()
      setCredentials(data || [])
    } catch (e: any) {
      setError(e.message || 'Failed to load integrations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const isConnected = (providerName: string) => {
    return credentials.some(
      (c) => c.provider.toLowerCase() === providerName.toLowerCase(),
    )
  }

  const getCredential = (providerName: string) => {
    return credentials.find(
      (c) => c.provider.toLowerCase() === providerName.toLowerCase(),
    )
  }

  const openConnect = (integration: Integration) => {
    setSelected(integration)
    setProvider(integration.provider)
    setSecret('')
    setLabel('')
    setError('')
    setMessage('')
  }

  const save = async () => {
    if (!provider || !secret.trim()) {
      setError('Please enter an API key.')
      return
    }

    setSaving(true)
    setError('')
    setMessage('')

    try {
      await api.createApiCredential(
        provider,
        secret.trim(),
        label.trim() || undefined,
      )

      setSecret('')
      setLabel('')
      setMessage(`${selected?.name || provider} connected successfully.`)

      await load()

      setTimeout(() => {
        setSelected(null)
        setMessage('')
      }, 1000)
    } catch (e: any) {
      setError(e.message || 'Failed to save API key')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (credential: Credential) => {
    const confirmed = window.confirm(
      `Remove ${credential.provider} integration?`,
    )

    if (!confirmed) return

    try {
      setError('')
      await api.deleteApiCredential(credential.id)
      await load()
      setMessage(`${credential.provider} disconnected.`)
    } catch (e: any) {
      setError(e.message || 'Failed to remove integration')
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-slate-100 rounded animate-pulse" />
        <div className="grid md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((x) => (
            <div
              key={x}
              className="h-48 bg-slate-100 rounded-xl animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Integrations
          </h1>

          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Connect the services your workspace uses for lead discovery,
            AI generation and email delivery.
          </p>
        </div>

        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-2 border px-3 py-2 rounded-lg text-sm hover:bg-slate-50"
        >
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
          {error}
        </div>
      )}

      {message && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 rounded-xl p-3 text-sm">
          {message}
        </div>
      )}

      {/* Security banner */}
      <div className="bg-slate-900 text-white rounded-xl p-5 mb-6">
        <div className="flex items-start gap-3">
          <KeyRound size={20} className="mt-0.5" />

          <div>
            <h2 className="font-semibold">
              Your API keys are protected
            </h2>

            <p className="text-sm text-slate-300 mt-1">
              Keys are stored through the backend credential system.
              The dashboard only displays a masked version after saving.
            </p>
          </div>
        </div>
      </div>

      {/* Integration cards */}
      <div className="grid md:grid-cols-2 gap-4">
        {INTEGRATIONS.map((integration) => {
          const connected = isConnected(integration.provider)
          const credential = getCredential(integration.provider)

          return (
            <div
              key={integration.id}
              className="bg-white border rounded-xl p-5 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-slate-100 flex items-center justify-center">
                    <KeyRound
                      size={20}
                      className="text-slate-600"
                    />
                  </div>

                  <div>
                    <h2 className="font-semibold text-slate-900">
                      {integration.name}
                    </h2>

                    <p className="text-xs text-slate-500">
                      {integration.category}
                    </p>
                  </div>
                </div>

                {connected ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium bg-green-100 text-green-700 px-2 py-1 rounded-md">
                    <CheckCircle2 size={13} />
                    Connected
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-medium bg-slate-100 text-slate-500 px-2 py-1 rounded-md">
                    <XCircle size={13} />
                    Not connected
                  </span>
                )}
              </div>

              <p className="text-sm text-slate-600 leading-relaxed mb-4">
                {integration.description}
              </p>

              {connected && credential && (
                <div className="bg-slate-50 border rounded-lg px-3 py-2 mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-500">
                        API credential
                      </p>

                      <p className="text-sm font-medium">
                        ••••••••{credential.last4 || '••••'}
                      </p>
                    </div>

                    {credential.label && (
                      <span className="text-xs text-slate-500">
                        {credential.label}
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => openConnect(integration)}
                  className={
                    connected
                      ? 'border border-slate-300 px-3 py-2 rounded-lg text-sm hover:bg-slate-50'
                      : 'bg-brand-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-brand-700'
                  }
                >
                  {connected ? 'Update key' : 'Connect'}
                </button>

                {connected && credential && (
                  <button
                    type="button"
                    onClick={() => remove(credential)}
                    className="inline-flex items-center gap-1.5 text-red-600 border border-red-200 px-3 py-2 rounded-lg text-sm hover:bg-red-50"
                  >
                    <Trash2 size={14} />
                    Remove
                  </button>
                )}

                {integration.docs && (
                  <a
                    href={integration.docs}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
                  >
                    Docs
                    <ExternalLink size={13} />
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Sending identity shortcut */}
      <div className="mt-6 bg-white border rounded-xl p-5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 className="font-semibold">
              Email sending identity
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Configure your sending domain, SPF and DKIM separately.
            </p>
          </div>

          <a
            href="/settings"
            className="text-sm text-brand-600 hover:underline"
          >
            Open sending settings →
          </a>
        </div>
      </div>

      {/* Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="text-lg font-semibold">
                  Connect {selected.name}
                </h2>

                <p className="text-xs text-slate-500 mt-1">
                  Add your API credential to enable this integration.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelected(null)}
                className="text-slate-400 hover:text-slate-700 text-xl"
              >
                ×
              </button>
            </div>

            <label className="block text-xs font-medium text-slate-600 mb-1">
              Label
            </label>

            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Production key"
              className="w-full border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />

            <label className="block text-xs font-medium text-slate-600 mb-1">
              API Key
            </label>

            <input
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Paste API key"
              autoComplete="off"
              className="w-full border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />

            {error && (
              <p className="text-sm text-red-600 mb-3">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={save}
                disabled={saving || !secret.trim()}
                className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
              >
                {saving ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}