import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import {
  Download,
  Phone,
  Globe,
  Target,
  MessageSquare,
  TrendingUp,
  Printer,
  ShieldCheck,
} from 'lucide-react'
import { api } from '../lib/api'
import { PageHeader, ErrorBanner, PageSkeleton } from '../components/ui'

type QualityMetrics = Awaited<ReturnType<typeof api.leadQualityMetrics>>

function RateBar({
  label,
  pct,
  icon: Icon,
  tone = 'brand',
}: {
  label: string
  pct: number
  icon: typeof Phone
  tone?: 'brand' | 'green' | 'amber'
}) {
  const bar =
    tone === 'green'
      ? 'bg-emerald-500'
      : tone === 'amber'
      ? 'bg-amber-500'
      : 'bg-brand-500'
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="flex items-center gap-2 text-slate-700 font-medium">
          <Icon size={15} className="text-slate-400" />
          {label}
        </span>
        <span className="font-semibold text-slate-900">{pct}%</span>
      </div>
      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${bar} rounded-full transition-all duration-700`}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
    </div>
  )
}

export default function LeadQuality() {
  const [data, setData] = useState<QualityMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)

  const load = async () => {
    setError('')
    try {
      const m = await api.leadQualityMetrics()
      setData(m)
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to load lead quality metrics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleExport = async () => {
    setExporting(true)
    try {
      await api.exportLeadsCsv()
    } catch (e: unknown) {
      setError((e as Error).message || 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  if (loading) return <PageSkeleton rows={5} />

  const funnel = data
    ? [
        { name: 'Total leads', value: data.totals.leads },
        { name: 'Strong fit', value: data.totals.strong_fit_score_ge_65 },
        { name: 'Contacted', value: data.totals.contacted },
        { name: 'Replied+', value: data.totals.replied_or_later },
      ]
    : []

  const colors = ['#94a3b8', '#38bdf8', '#0ea5e9', '#16a34a']

  return (
    <div className="max-w-5xl">
      <PageHeader
        title="Lead Quality Report"
        description="Provenance-backed proof — not a vanity AI score. Rates you can put in a client deck."
        actions={
          <>
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-slate-50"
            >
              <Printer size={16} />
              Print / PDF
            </button>
            <button
              type="button"
              onClick={handleExport}
              disabled={exporting}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              <Download size={16} />
              {exporting ? 'Exporting…' : 'Export CSV'}
            </button>
          </>
        }
      />

      {error && (
        <ErrorBanner message={error} onRetry={load} onDismiss={() => setError('')} />
      )}

      {data && (
        <div className="space-y-6">
          {/* Headline stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                label: 'Total leads',
                value: data.totals.leads,
                icon: Target,
              },
              {
                label: 'Messages sent',
                value: data.totals.messages_sent,
                icon: MessageSquare,
              },
              {
                label: 'Reply rate (of contacted)',
                value: `${data.rates.reply_pct_of_contacted}%`,
                icon: TrendingUp,
              },
              {
                label: 'Strong-fit leads',
                value: `${data.rates.strong_fit_pct}%`,
                icon: ShieldCheck,
              },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="bg-white border rounded-xl p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <Icon size={16} />
                  <span className="text-xs font-medium uppercase tracking-wide">
                    {label}
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900">{value}</p>
              </div>
            ))}
          </div>

          {/* Funnel chart */}
          <div className="bg-white border rounded-xl p-5">
            <h2 className="font-semibold text-slate-900 mb-4">
              Outreach funnel
            </h2>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={funnel} margin={{ left: 0, right: 12 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: '#f1f5f9' }}
                    contentStyle={{ borderRadius: 8, fontSize: 13 }}
                  />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {funnel.map((_, i) => (
                      <Cell key={i} fill={colors[i % colors.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Coverage rates */}
          <div className="bg-white border rounded-xl p-5 space-y-5">
            <h2 className="font-semibold text-slate-900">Data coverage</h2>
            <RateBar
              label="Phone coverage"
              pct={data.rates.phone_coverage_pct}
              icon={Phone}
            />
            <RateBar
              label="Website present"
              pct={data.rates.website_present_pct}
              icon={Globe}
              tone="amber"
            />
            <RateBar
              label="Contacted"
              pct={data.rates.contacted_pct}
              icon={MessageSquare}
              tone="brand"
            />
            <RateBar
              label="Reply rate (of all leads)"
              pct={data.rates.reply_pct_of_leads}
              icon={TrendingUp}
              tone="green"
            />
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Method: {data.method.scoring} — not {data.method.not}. {data.method.note} ·
            As of {new Date(data.as_of).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  )
}
