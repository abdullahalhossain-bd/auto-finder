import { useEffect, useMemo, useState, FormEvent } from 'react'
import { api } from '../lib/api'
import { SuppressionEntry } from '../types'
import {
  ShieldBan,
  Plus,
  Search,
  RefreshCw,
  Mail,
  Phone,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Users,
} from 'lucide-react'
import { PageSkeleton, CardListSkeleton, EmptyState, ErrorBanner } from '../components/ui'

export default function Suppression() {
  const [items, setItems] = useState<SuppressionEntry[]>([])
  const [value, setValue] = useState('')
  const [reason, setReason] = useState('')

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [adding, setAdding] = useState(false)

  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)

    setError('')

    try {
      const data = await api.listSuppression()
      setItems(data)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setError(e.message || 'Failed to load suppression list')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const normalizeContact = (input: string) => {
    return input.trim().toLowerCase()
  }

  const looksLikeEmail = (input: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input)
  }

  const looksLikePhone = (input: string) => {
    const cleaned = input.replace(/[\s().-]/g, '')

    return /^\+?[0-9]{7,15}$/.test(cleaned)
  }

  const getContactType = (input: string): 'email' | 'phone' | 'unknown' => {
    const normalized = normalizeContact(input)

    if (looksLikeEmail(normalized)) return 'email'
    if (looksLikePhone(normalized)) return 'phone'

    return 'unknown'
  }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()

    setError('')
    setSuccess('')

    const contact = normalizeContact(value)

    if (!contact) {
      setError('Please enter an email address or phone number.')
      return
    }

    const type = getContactType(contact)

    if (type === 'unknown') {
      setError(
        'Please enter a valid email address or phone number.'
      )
      return
    }

    // Frontend duplicate check for faster UX.
    const duplicate = items.some(
      (item) =>
        normalizeContact(item.contact_value) === contact
    )

    if (duplicate) {
      setError(
        'This contact is already on the Do Not Contact list.'
      )
      return
    }

    setAdding(true)

    try {
      await api.addSuppression(
        contact,
        reason.trim() || undefined
      )

      setValue('')
      setReason('')

      setSuccess(
        `${type === 'email' ? 'Email' : 'Phone number'} added to the Do Not Contact list.`
      )

      await load()
    } catch (err: unknown) {
      const e = err as { message?: string }

      setError(
        e.message || 'Failed to add contact to suppression list.'
      )
    } finally {
      setAdding(false)
    }
  }

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) return items

    return items.filter((item) => {
      const contact = item.contact_value?.toLowerCase() || ''
      const reasonText = item.reason?.toLowerCase() || ''

      return (
        contact.includes(query) ||
        reasonText.includes(query)
      )
    })
  }, [items, search])

  const emailCount = useMemo(() => {
    return items.filter(
      (item) => getContactType(item.contact_value) === 'email'
    ).length
  }, [items])

  const phoneCount = useMemo(() => {
    return items.filter(
      (item) => getContactType(item.contact_value) === 'phone'
    ).length
  }, [items])

  const formatDate = (date: string) => {
    const parsed = new Date(date)

    if (Number.isNaN(parsed.getTime())) {
      return '—'
    }

    return parsed.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatDateTime = (date: string) => {
    const parsed = new Date(date)

    if (Number.isNaN(parsed.getTime())) {
      return '—'
    }

    return parsed.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  if (loading) {
    return <PageSkeleton rows={4} />
  }

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
              <ShieldBan size={21} />
            </div>

            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                Do Not Contact
              </h1>

              <p className="text-slate-500 text-sm mt-1">
                Contacts on this list will be excluded from outreach.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => load(true)}
          disabled={refreshing}
          className="inline-flex items-center justify-center gap-2 px-3 py-2 border rounded-lg text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          {refreshing ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <RefreshCw size={16} />
          )}

          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mb-5 flex items-start gap-3 p-3.5 bg-red-50 border border-red-100 text-red-700 rounded-xl text-sm">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />

          <div className="flex-1">
            {error}
          </div>

          <button
            type="button"
            onClick={() => setError('')}
            className="text-red-500 hover:text-red-700 font-medium"
          >
            ×
          </button>
        </div>
      )}

      {success && (
        <div className="mb-5 flex items-start gap-3 p-3.5 bg-green-50 border border-green-100 text-green-700 rounded-xl text-sm">
          <CheckCircle2 size={18} className="shrink-0 mt-0.5" />

          <div className="flex-1">
            {success}
          </div>

          <button
            type="button"
            onClick={() => setSuccess('')}
            className="text-green-600 hover:text-green-800 font-medium"
          >
            ×
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard
          icon={<Users size={18} />}
          label="Total Suppressed"
          value={items.length}
        />

        <StatCard
          icon={<Mail size={18} />}
          label="Emails"
          value={emailCount}
        />

        <StatCard
          icon={<Phone size={18} />}
          label="Phone Numbers"
          value={phoneCount}
        />
      </div>

      {/* Add contact */}
      <div className="bg-white border rounded-xl p-5 mb-6">
        <div className="flex items-start gap-3 mb-5">
          <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center shrink-0">
            <Plus size={18} />
          </div>

          <div>
            <h2 className="font-semibold text-slate-900">
              Add Contact
            </h2>

            <p className="text-xs text-slate-500 mt-1">
              Add an email address or phone number that should never
              receive outreach from this organization.
            </p>
          </div>
        </div>

        <form onSubmit={handleAdd}>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3">
            <div>
              <label
                htmlFor="suppression-contact"
                className="block text-xs font-medium text-slate-600 mb-1.5"
              >
                Email or Phone
              </label>

              <input
                id="suppression-contact"
                value={value}
                onChange={(e) => {
                  setValue(e.target.value)
                  setError('')
                  setSuccess('')
                }}
                disabled={adding}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:bg-slate-50"
                placeholder="email@example.com or +48123456789"
                autoComplete="off"
              />
            </div>

            <div>
              <label
                htmlFor="suppression-reason"
                className="block text-xs font-medium text-slate-600 mb-1.5"
              >
                Reason
                <span className="font-normal text-slate-400">
                  {' '}
                  (optional)
                </span>
              </label>

              <input
                id="suppression-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={adding}
                maxLength={500}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:bg-slate-50"
                placeholder="Requested removal"
              />
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={adding || !value.trim()}
                className="w-full md:w-auto inline-flex items-center justify-center gap-2 bg-brand-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {adding ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <Plus size={16} />
                    Add
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        <div className="mt-4 flex items-start gap-2 text-xs text-slate-500 bg-slate-50 border rounded-lg p-3">
          <ShieldBan size={15} className="shrink-0 mt-0.5 text-slate-400" />

          <p>
            Suppressed contacts should be blocked from future outreach
            even if they appear in a campaign or lead list.
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Suppressed Contacts
          </h2>

          <p className="text-xs text-slate-500 mt-1">
            {search
              ? `${filteredItems.length} matching ${
                  filteredItems.length === 1 ? 'contact' : 'contacts'
                }`
              : `${items.length} ${
                  items.length === 1 ? 'contact' : 'contacts'
                }`}
          </p>
        </div>

        {items.length > 0 && (
          <div className="relative w-full sm:w-72">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search contacts or reasons..."
              className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />

            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            )}
          </div>
        )}
      </div>

      {/* Empty state */}
      {items.length === 0 ? (
        <EmptyState
          icon={<ShieldBan size={28} />}
          title="No suppressed contacts"
          description="Contacts who request not to be contacted can be added here. They will be excluded from future outreach."
        />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          icon={<Search size={28} />}
          title="No matching contacts"
          description="Try a different search term."
          actionLabel="Clear search"
          onAction={() => setSearch('')}
        />
      ) : (
        <>
        {/* Mobile cards */}
        <div className="md:hidden space-y-3">
          {filteredItems.map((item) => {
            const type = getContactType(item.contact_value)
            return (
              <div
                key={item.id}
                className="bg-white border border-slate-200 rounded-xl p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                    {type === 'email' ? <Mail size={16} /> : <Phone size={16} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-slate-900 break-all text-sm">
                      {item.contact_value}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-slate-500">
                      <span className="capitalize px-2 py-0.5 rounded bg-slate-100">
                        {type}
                      </span>
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                    {item.reason && (
                      <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                        {item.reason}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
          <p className="text-xs text-slate-500 text-center pt-1">
            Showing {filteredItems.length} of {items.length} suppressed contacts
          </p>
        </div>

        {/* Desktop table */}
        <div className="hidden md:block bg-white border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr>
                  <th className="px-4 py-3 font-medium">
                    Contact
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Type
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Reason
                  </th>

                  <th className="px-4 py-3 font-medium">
                    Added
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredItems.map((item) => {
                  const type = getContactType(
                    item.contact_value
                  )

                  return (
                    <tr
                      key={item.id}
                      className="border-t hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-lg bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                            {type === 'email' ? (
                              <Mail size={15} />
                            ) : (
                              <Phone size={15} />
                            )}
                          </div>

                          <span className="font-medium text-slate-800 break-all">
                            {item.contact_value}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-1 rounded-md bg-slate-100 text-slate-600 text-xs capitalize">
                          {type}
                        </span>
                      </td>

                      <td className="px-4 py-3 text-slate-500 max-w-xs">
                        <span className="line-clamp-2">
                          {item.reason || '—'}
                        </span>
                      </td>

                      <td
                        className="px-4 py-3 text-slate-500 whitespace-nowrap"
                        title={formatDateTime(item.created_at)}
                      >
                        {formatDate(item.created_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="border-t bg-slate-50 px-4 py-3 text-xs text-slate-500">
            Showing {filteredItems.length} of {items.length}{' '}
            suppressed contacts
          </div>
        </div>
        </>
      )}

      {/* Compliance note */}
      <div className="mt-6 p-4 bg-amber-50 border border-amber-100 rounded-xl">
        <div className="flex items-start gap-3">
          <AlertCircle
            size={18}
            className="text-amber-600 shrink-0 mt-0.5"
          />

          <div className="text-xs text-amber-800">
            <p className="font-semibold mb-1">
              Important
            </p>

            <p>
              Adding a contact here only protects them if the backend
              suppression check is enforced before message delivery.
              Make sure every outbound sending path checks this list
              before sending.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: number
}) {
  return (
    <div className="bg-white border rounded-xl p-5">
      <div className="flex items-center gap-2 text-slate-500 text-sm mb-2">
        {icon}
        <span>{label}</span>
      </div>

      <p className="text-3xl font-bold text-slate-900">
        {value}
      </p>
    </div>
  )
}