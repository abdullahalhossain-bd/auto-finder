import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Link } from 'react-router-dom'
import {
  Building2,
  Mail,
  KeyRound,
  Users,
  Download,
  Trash2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react'
import { PageSkeleton, CardListSkeleton, EmptyState, ErrorBanner } from '../components/ui'

type Organization = {
  id: string
  name: string
  plan: string
}

type SendingIdentity = {
  configured?: boolean
  from_name?: string
  from_address?: string
  verified_domain?: string
  spf_verified?: boolean
  dkim_verified?: boolean
  can_send?: boolean
  sending_paused?: boolean
  pause_reason?: string
  dns_hint?: unknown
}

type ApiCredential = {
  id: string
  provider: string
  last4?: string
  label?: string
}

type Invite = {
  id: string
  email: string
  role: string
  status: string
}

export default function Settings() {
  const [org, setOrg] = useState<Organization | null>(null)
  const [identity, setIdentity] = useState<SendingIdentity | null>(null)
  const [creds, setCreds] = useState<ApiCredential[]>([])
  const [invites, setInvites] = useState<Invite[]>([])

  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)

  const [fromName, setFromName] = useState('Outreach')
  const [provider, setProvider] = useState('google_places')
  const [secret, setSecret] = useState('')
  const [label, setLabel] = useState('')

  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')

  const [savingIdentity, setSavingIdentity] = useState(false)
  const [verifyingIdentity, setVerifyingIdentity] = useState(false)
  const [savingCred, setSavingCred] = useState(false)
  const [deletingCred, setDeletingCred] = useState('')
  const [sendingInvite, setSendingInvite] = useState(false)
  const [revokingInvite, setRevokingInvite] = useState('')

  const clearMessages = () => {
    setError('')
    setMsg('')
  }

  const load = async () => {
    setLoading(true)
    setError('')

    try {
      const [me, sendingIdentity, credentials, inviteList] = await Promise.all([
        api.getMe(),
        api.getSendingIdentity().catch(() => null),
        api.listApiCredentials().catch(() => []),
        api.listInvites().catch(() => []),
      ])

      setOrg(me)
      setIdentity(sendingIdentity)
      setCreds(credentials || [])
      setInvites(inviteList || [])

      if (sendingIdentity?.from_name) {
        setFromName(sendingIdentity.from_name)
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const assignPlatform = async () => {
    clearMessages()

    if (!fromName.trim()) {
      setError('Please enter a From name.')
      return
    }

    setSavingIdentity(true)

    try {
      const row = await api.upsertSendingIdentity({
        use_platform_subdomain: true,
        from_name: fromName.trim(),
      })

      setIdentity(row)
      setMsg(
        'Platform sending identity configured. Complete SPF/DKIM verification before sending.'
      )
    } catch (e: any) {
      setError(e?.message || 'Failed to configure sending identity')
    } finally {
      setSavingIdentity(false)
    }
  }

  const verify = async () => {
    clearMessages()
    setVerifyingIdentity(true)

    try {
      const row = await api.verifySendingIdentity(true, true)
      setIdentity(row)
      setMsg('SPF + DKIM marked verified.')
    } catch (e: any) {
      setError(e?.message || 'Verification failed')
    } finally {
      setVerifyingIdentity(false)
    }
  }

  const saveCred = async () => {
    clearMessages()

    if (!secret.trim()) {
      setError('Please enter an API key.')
      return
    }

    setSavingCred(true)

    try {
      await api.createApiCredential(
        provider,
        secret.trim(),
        label.trim() || undefined
      )

      setSecret('')
      setLabel('')
      setMsg('API credential saved successfully.')
      await load()
    } catch (e: any) {
      setError(e?.message || 'Failed to save API credential')
    } finally {
      setSavingCred(false)
    }
  }

  const removeCred = async (id: string) => {
    if (!window.confirm('Remove this API credential?')) return

    clearMessages()
    setDeletingCred(id)

    try {
      await api.deleteApiCredential(id)
      setCreds((current) => current.filter((c) => c.id !== id))
      setMsg('API credential removed.')
    } catch (e: any) {
      setError(e?.message || 'Failed to remove credential')
    } finally {
      setDeletingCred('')
    }
  }

  const sendInvite = async () => {
    clearMessages()

    const email = inviteEmail.trim()

    if (!email) {
      setError('Please enter an email address.')
      return
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address.')
      return
    }

    setSendingInvite(true)

    try {
      const r = await api.createInvite(email, inviteRole)

      setMsg(
        r.invite_token_dev
          ? `Invite created. Dev token: ${r.invite_token_dev}`
          : 'Invite created successfully.'
      )

      setInviteEmail('')
      await load()
    } catch (e: any) {
      setError(e?.message || 'Failed to create invite')
    } finally {
      setSendingInvite(false)
    }
  }

  const revokeInvite = async (id: string) => {
    if (!window.confirm('Revoke this invitation?')) return

    clearMessages()
    setRevokingInvite(id)

    try {
      await api.revokeInvite(id)

      setInvites((current) => current.filter((i) => i.id !== id))
      setMsg('Invitation revoked.')
    } catch (e: any) {
      setError(e?.message || 'Failed to revoke invitation')
    } finally {
      setRevokingInvite('')
    }
  }

  if (loading) {
    return <PageSkeleton />
  }

  return (
    <div className="max-w-3xl space-y-6 pb-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage your organization, sending identity, API keys and team.
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

      {/* Global messages */}
      {error && (
        <ErrorBanner message={error} onDismiss={() => setError('')} />
      )}

      {msg && (
        <div className="flex items-start gap-2 p-3 bg-green-50 border border-green-100 text-green-700 rounded-lg text-sm">
          <CheckCircle2 size={17} className="mt-0.5 shrink-0" />
          <span>{msg}</span>
        </div>
      )}

      {/* Organization */}
      <section className="bg-white border rounded-xl overflow-hidden">
        <div className="p-5 border-b">
          <div className="flex items-center gap-2">
            <Building2 size={19} className="text-slate-500" />
            <h2 className="font-semibold">Organization</h2>
          </div>
        </div>

        <div className="p-5">
          {org ? (
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-slate-500">Name:</span>{' '}
                <strong>{org.name}</strong>
              </div>

              <div>
                <span className="text-slate-500">Plan:</span>{' '}
                <span className="capitalize font-medium">{org.plan}</span>

                <Link
                  to="/billing"
                  className="text-brand-600 hover:underline text-xs ml-3"
                >
                  Manage billing →
                </Link>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() =>
                    api.exportOrg().catch((e) => setError(e.message))
                  }
                  className="inline-flex items-center gap-2 border px-3 py-2 rounded-lg text-sm hover:bg-slate-50"
                >
                  <Download size={15} />
                  Export my data
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Organization information unavailable.
            </p>
          )}
        </div>
      </section>

      {/* Sending Identity */}
      <section className="bg-white border rounded-xl overflow-hidden">
        <div className="p-5 border-b">
          <div className="flex items-center gap-2">
            <Mail size={19} className="text-slate-500" />
            <div>
              <h2 className="font-semibold">Sending Identity</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Configure the identity used for outbound messages.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5">
          {identity?.configured === false && (
            <div className="flex gap-2 p-3 bg-amber-50 border border-amber-100 text-amber-800 rounded-lg text-sm mb-4">
              <AlertTriangle size={17} className="mt-0.5 shrink-0" />
              <span>Sending identity is not configured yet.</span>
            </div>
          )}

          {identity?.from_address && (
            <div className="bg-slate-50 border rounded-lg p-4 text-sm space-y-2 mb-5">
              <div>
                <span className="text-slate-500">From:</span>{' '}
                {identity.from_name || '—'} &lt;{identity.from_address}&gt;
              </div>

              <div>
                <span className="text-slate-500">Domain:</span>{' '}
                {identity.verified_domain || '—'}
              </div>

              <div className="flex flex-wrap gap-3 pt-1">
                <VerificationStatus
                  label="SPF"
                  verified={!!identity.spf_verified}
                />
                <VerificationStatus
                  label="DKIM"
                  verified={!!identity.dkim_verified}
                />
                <VerificationStatus
                  label="Can send"
                  verified={!!identity.can_send}
                />
              </div>

              {identity.sending_paused && (
                <div className="text-red-600 pt-1">
                  Sending paused: {identity.pause_reason || 'Unknown reason'}
                </div>
              )}

              {!!identity.dns_hint && (
                <details className="pt-2">
                  <summary className="cursor-pointer text-xs text-slate-500">
                    View DNS instructions
                  </summary>

                  <pre className="text-xs bg-white border p-3 rounded-lg mt-2 overflow-auto">
                    {JSON.stringify(identity.dns_hint, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                From name
              </label>

              <input
                className="border rounded-lg px-3 py-2 text-sm w-full max-w-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={fromName}
                onChange={(e) => setFromName(e.target.value)}
                placeholder="e.g. Abdullah from MyCompany"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={assignPlatform}
                disabled={savingIdentity}
                className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
              >
                {savingIdentity
                  ? 'Configuring...'
                  : 'Assign platform subdomain'}
              </button>

              <button
                type="button"
                onClick={verify}
                disabled={verifyingIdentity}
                className="border px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
              >
                {verifyingIdentity
                  ? 'Verifying...'
                  : 'Mark SPF/DKIM verified'}
              </button>
            </div>

            <p className="text-xs text-slate-500">
              In production, SPF/DKIM should be verified against actual DNS
              records rather than manually marked as verified.
            </p>
          </div>
        </div>
      </section>

      {/* API Credentials */}
      <section className="bg-white border rounded-xl overflow-hidden">
        <div className="p-5 border-b">
          <div className="flex items-center gap-2">
            <KeyRound size={19} className="text-slate-500" />
            <div>
              <h2 className="font-semibold">API Credentials</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Store provider credentials for discovery and AI services.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5">
          <div className="space-y-2 mb-5">
            {creds.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between gap-3 border rounded-lg px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {c.provider}
                  </p>

                  <p className="text-xs text-slate-500">
                    {c.label ? `${c.label} · ` : ''}
                    {c.last4 ? `••••${c.last4}` : 'Credential stored'}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => removeCred(c.id)}
                  disabled={deletingCred === c.id}
                  className="inline-flex items-center gap-1 text-red-600 text-xs hover:text-red-700 disabled:opacity-50"
                >
                  <Trash2 size={14} />
                  {deletingCred === c.id ? 'Removing...' : 'Remove'}
                </button>
              </div>
            ))}

            {creds.length === 0 && (
              <EmptyState
                title="No API credentials"
                description="Connect ESP or Places keys when you are ready to send or enrich discovery."
                className="py-8"
              />
            )}
          </div>

          <div className="border-t pt-5">
            <p className="text-sm font-medium mb-3">Add credential</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <select
                className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="google_places">Google Places</option>
                <option value="groq">Groq</option>
                <option value="resend">Resend</option>
              </select>

              <input
                className="border rounded-lg px-3 py-2 text-sm"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="Label (optional)"
              />

              <input
                className="border rounded-lg px-3 py-2 text-sm"
                type="password"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                placeholder="API key / secret"
              />
            </div>

            <button
              type="button"
              onClick={saveCred}
              disabled={savingCred}
              className="mt-3 bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-900 disabled:opacity-50"
            >
              {savingCred ? 'Saving...' : 'Save credential'}
            </button>

            <p className="text-xs text-slate-500 mt-2">
              Credentials should remain encrypted at rest and should never be
              displayed in full after saving.
            </p>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="bg-white border rounded-xl overflow-hidden">
        <div className="p-5 border-b">
          <div className="flex items-center gap-2">
            <Users size={19} className="text-slate-500" />
            <div>
              <h2 className="font-semibold">Team Invites</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Invite people to collaborate on this organization.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5">
          <div className="space-y-2 mb-5">
            {invites.map((invite) => (
              <div
                key={invite.id}
                className="flex items-center justify-between gap-3 border rounded-lg px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">
                    {invite.email}
                  </p>

                  <p className="text-xs text-slate-500 capitalize">
                    {invite.role} · {invite.status}
                  </p>
                </div>

                {invite.status === 'pending' && (
                  <button
                    type="button"
                    onClick={() => revokeInvite(invite.id)}
                    disabled={revokingInvite === invite.id}
                    className="text-xs text-red-600 hover:text-red-700 disabled:opacity-50"
                  >
                    {revokingInvite === invite.id
                      ? 'Revoking...'
                      : 'Revoke'}
                  </button>
                )}
              </div>
            ))}

            {invites.length === 0 && (
              <EmptyState
                title="No invitations yet"
                description="Invite teammates to collaborate on campaigns and approvals."
                className="py-8"
              />
            )}
          </div>

          <div className="border-t pt-5">
            <p className="text-sm font-medium mb-3">Invite teammate</p>

            <div className="flex flex-col md:flex-row gap-2">
              <input
                className="border rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-brand-500"
                type="email"
                placeholder="colleague@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />

              <select
                className="border rounded-lg px-3 py-2 text-sm"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>

              <button
                type="button"
                onClick={sendInvite}
                disabled={sendingInvite}
                className="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-900 disabled:opacity-50"
              >
                {sendingInvite ? 'Inviting...' : 'Invite'}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Security note */}
      <section className="flex gap-3 bg-slate-50 border rounded-xl p-4 text-sm text-slate-600">
        <ShieldCheck size={20} className="shrink-0 text-slate-500" />

        <div>
          <p className="font-medium text-slate-700">
            Security & sending safety
          </p>

          <p className="text-xs mt-1">
            API credentials are write-only from the UI. Sending should remain
            blocked until the sending identity is properly verified, and
            suppressed contacts should never receive outreach.
          </p>
        </div>
      </section>
    </div>
  )
}

function VerificationStatus({
  label,
  verified,
}: {
  label: string
  verified: boolean
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium ${
        verified ? 'text-green-700' : 'text-red-600'
      }`}
    >
      {verified ? (
        <CheckCircle2 size={14} />
      ) : (
        <XCircle size={14} />
      )}
      {label}: {verified ? 'Verified' : 'Not verified'}
    </span>
  )
}