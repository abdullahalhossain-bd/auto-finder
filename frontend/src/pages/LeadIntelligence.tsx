import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { Lead } from '../types'
import {
  ArrowLeft,
  Globe,
  Mail,
  Phone,
  Calendar,
  MapPin,
  Target,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  MessageSquare,
} from 'lucide-react'

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

export default function LeadIntelligence() {
  const { id } = useParams<{ id: string }>()

  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return

    api
      .getLead(id)
      .then(setLead)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const updateStage = async (stage: string) => {
    if (!id) return

    setSaving(true)
    setError('')

    try {
      const updated = await api.updateLead(id, { stage })
      setLead(updated)
    } catch (e: any) {
      setError(e.message || 'Failed to update stage')
    } finally {
      setSaving(false)
    }
  }

  const score = useMemo(() => {
    if (!lead?.opportunity_score) return 0
    return Math.round(lead.opportunity_score)
  }, [lead])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-slate-100 rounded animate-pulse" />
        <div className="h-40 bg-slate-100 rounded-xl animate-pulse" />
        <div className="grid md:grid-cols-3 gap-4">
          {[1, 2, 3].map((x) => (
            <div key={x} className="h-36 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!lead) {
    return <div className="text-red-600">{error || 'Lead not found'}</div>
  }

  const data = lead as any
  const website = data.website || data.website_url || data.business_website || ''
  const email = data.email || data.contact_email || data.business_email || ''
  const phone = data.phone || data.contact_phone || data.business_phone || ''
  const address = data.address || data.location || ''
  const mapsUrl = data.google_maps_url || data.maps_url || ''

  const websiteIntel =
    data.score_breakdown?.website_intelligence &&
    typeof data.score_breakdown.website_intelligence === 'object'
      ? data.score_breakdown.website_intelligence
      : null

  const qualityScore =
    typeof websiteIntel?.quality_score === 'number'
      ? Math.round(websiteIntel.quality_score)
      : null

  const weakReasons = Array.isArray(websiteIntel?.weak_reasons)
    ? websiteIntel.weak_reasons
    : []

  const bookingVendor = websiteIntel?.booking_vendor || null
  const cms = Array.isArray(websiteIntel?.cms) ? websiteIntel.cms : []
  const analytics = Array.isArray(websiteIntel?.analytics) ? websiteIntel.analytics : []
  const socialLinks = Array.isArray(websiteIntel?.social_links) ? websiteIntel.social_links : []
  const emails = Array.isArray(websiteIntel?.emails) ? websiteIntel.emails : []
  const phoneLinks = Array.isArray(websiteIntel?.phone_links) ? websiteIntel.phone_links : []
  const seo = websiteIntel?.seo && typeof websiteIntel.seo === 'object' ? websiteIntel.seo : null
  const accessibility =
    websiteIntel?.accessibility && typeof websiteIntel.accessibility === 'object'
      ? websiteIntel.accessibility
      : null

  const hasWebsite = Boolean(website)
  const hasEmail = Boolean(email || emails.length)
  const hasPhone = Boolean(phone || phoneLinks.length)
  const websiteWeak = Boolean(
    data.score_breakdown?.website_weak || weakReasons.length || (qualityScore !== null && qualityScore < 60),
  )

  const scoreLabel =
    score >= 80
      ? 'High opportunity'
      : score >= 60
        ? 'Good opportunity'
        : score >= 40
          ? 'Moderate opportunity'
          : 'Low opportunity'

  const scoreClass =
    score >= 80
      ? 'text-green-600'
      : score >= 60
        ? 'text-blue-600'
        : score >= 40
          ? 'text-yellow-600'
          : 'text-slate-500'

  return (
    <div className="max-w-6xl">
      <Link
        to={`/campaigns/${lead.campaign_id}`}
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-5"
      >
        <ArrowLeft size={16} />
        Back to campaign
      </Link>

      {error && (
        <div className="mb-5 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white border rounded-xl p-6 mb-5">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-5">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium px-2 py-1 rounded bg-brand-50 text-brand-700">
                Lead Intelligence
              </span>
              {lead.stage && (
                <span className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 capitalize">
                  {lead.stage.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              {lead.business_name || 'Unnamed business'}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              {lead.business_category || 'Business'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs text-slate-500">Opportunity Score</p>
              <p className={`text-4xl font-bold ${scoreClass}`}>{score || '—'}</p>
              <p className="text-xs text-slate-500">{scoreLabel}</p>
            </div>
            <div className="w-16 h-16 rounded-full border-4 border-slate-100 flex items-center justify-center">
              <Target size={27} className={scoreClass} />
            </div>
          </div>
        </div>

        <div className="mt-5 pt-5 border-t flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-500">Pipeline stage:</span>
          <select
            value={lead.stage || 'new'}
            disabled={saving}
            onChange={(e) => updateStage(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            {STAGES.map((stage) => (
              <option key={stage} value={stage}>
                {stage.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          <Link
            to={`/leads/${lead.id}`}
            className="inline-flex items-center gap-1.5 border px-3 py-2 rounded-lg text-sm hover:bg-slate-50"
          >
            <MessageSquare size={15} />
            Outreach
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <InsightCard
          icon={<Globe size={18} />}
          label="Website"
          value={!hasWebsite ? 'Missing' : websiteWeak ? 'Needs work' : 'Healthy'}
          good={!hasWebsite ? false : !websiteWeak}
          warning={!hasWebsite || websiteWeak}
        />
        <InsightCard
          icon={<Mail size={18} />}
          label="Email"
          value={hasEmail ? 'Available' : 'Not found'}
          good={hasEmail}
        />
        <InsightCard
          icon={<Phone size={18} />}
          label="Phone"
          value={hasPhone ? 'Available' : 'Not found'}
          good={hasPhone}
        />
        <InsightCard
          icon={<Sparkles size={18} />}
          label="AI opportunity"
          value={scoreLabel}
          good={score >= 60}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          <section className="bg-white border rounded-xl p-5">
            <h2 className="font-semibold mb-4">Business information</h2>
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <InfoRow label="Business name" value={lead.business_name} />
              <InfoRow label="Category" value={lead.business_category} />
              <InfoRow label="Email" value={email || emails[0]} href={(email || emails[0]) ? `mailto:${email || emails[0]}` : undefined} />
              <InfoRow label="Phone" value={phone || phoneLinks[0]} href={(phone || phoneLinks[0]) ? `tel:${phone || phoneLinks[0]}` : undefined} />
              <InfoRow label="Location" value={address} icon={<MapPin size={15} />} />
              <InfoRow label="Website" value={website} href={website} icon={<Globe size={15} />} />
            </div>
            {mapsUrl && (
              <a
                href={mapsUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-brand-600 text-sm mt-5 hover:underline"
              >
                Open Google Maps
                <ExternalLink size={14} />
              </a>
            )}
          </section>

          {websiteIntel && (
            <WebsiteIntelligenceCard
              website={website}
              qualityScore={qualityScore}
              weakReasons={weakReasons}
              bookingVendor={bookingVendor}
              cms={cms}
              analytics={analytics}
              socialLinks={socialLinks}
              seo={seo}
              accessibility={accessibility}
              forms={websiteIntel.forms}
              hasContactForm={websiteIntel.has_contact_form}
              hasCta={websiteIntel.has_cta}
              wordCount={websiteIntel.word_count}
              images={websiteIntel.images}
              scripts={websiteIntel.scripts}
              externalScripts={websiteIntel.external_scripts}
            />
          )}

          <section className="bg-white border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Target size={18} className="text-brand-600" />
              <h2 className="font-semibold">Opportunity analysis</h2>
            </div>
            {lead.score_breakdown ? (
              <div className="space-y-3">
                {Object.entries(lead.score_breakdown)
                  .filter(([key]) => key !== 'website_intelligence')
                  .map(([key, value]) => (
                    <ScoreRow key={key} label={key.replace(/_/g, ' ')} value={value} />
                  ))}
              </div>
            ) : (
              <div className="bg-slate-50 rounded-lg p-5 text-sm text-slate-500">
                No detailed score breakdown available.
              </div>
            )}
          </section>

          <section className="bg-white border rounded-xl p-5">
            <h2 className="font-semibold mb-4">Data confidence</h2>
            {lead.confidence_summary ? (
              <div className="grid md:grid-cols-2 gap-3">
                {Object.entries(lead.confidence_summary).map(([key, value]) => (
                  <div key={key} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm capitalize text-slate-600">{key.replace(/_/g, ' ')}</span>
                      <span className="text-sm font-semibold">{String(value)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No confidence data available.</p>
            )}
          </section>
        </div>

        <div className="space-y-5">
          <section className="bg-slate-900 text-white rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={18} />
              <h2 className="font-semibold">Recommended action</h2>
            </div>
            {score >= 80 ? (
              <p className="text-sm text-slate-300 leading-relaxed">
                High-value prospect. Review the website evidence and create a personalized outreach message.
              </p>
            ) : score >= 60 ? (
              <p className="text-sm text-slate-300 leading-relaxed">
                Promising prospect. Verify the available contact information before outreach.
              </p>
            ) : (
              <p className="text-sm text-slate-300 leading-relaxed">
                Lower-priority prospect. Consider reviewing the lead before spending outreach capacity.
              </p>
            )}
            <Link
              to={`/leads/${lead.id}`}
              className="mt-4 inline-flex items-center justify-center gap-2 w-full bg-white text-slate-900 rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100"
            >
              <MessageSquare size={15} />
              Create outreach
            </Link>
          </section>

          <section className="bg-white border rounded-xl p-5">
            <h2 className="font-semibold mb-4">Contactability</h2>
            <CheckItem label="Website available" value={hasWebsite} />
            <CheckItem label="Email available" value={hasEmail} />
            <CheckItem label="Phone available" value={hasPhone} />
            <CheckItem label="Booking detected" value={Boolean(bookingVendor)} />
            <CheckItem label="Lead is contactable" value={lead.stage !== 'do_not_contact'} />
          </section>

          <section className="bg-white border rounded-xl p-5">
            <h2 className="font-semibold mb-4">Lead metadata</h2>
            <div className="space-y-3 text-sm">
              <InfoRow label="Lead ID" value={lead.id} />
              <InfoRow label="Campaign ID" value={lead.campaign_id} />
              {data.created_at && (
                <InfoRow label="Created" value={new Date(data.created_at).toLocaleString()} icon={<Calendar size={15} />} />
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function WebsiteIntelligenceCard({
  website,
  qualityScore,
  weakReasons,
  bookingVendor,
  cms,
  analytics,
  socialLinks,
  seo,
  accessibility,
  forms,
  hasContactForm,
  hasCta,
  wordCount,
  images,
  scripts,
  externalScripts,
}: {
  website: string
  qualityScore: number | null
  weakReasons: string[]
  bookingVendor: string | null
  cms: string[]
  analytics: string[]
  socialLinks: string[]
  seo: Record<string, unknown> | null
  accessibility: Record<string, unknown> | null
  forms: unknown
  hasContactForm: unknown
  hasCta: unknown
  wordCount: unknown
  images: unknown
  scripts: unknown
  externalScripts: unknown
}) {
  const score = qualityScore ?? 0
  const status = score >= 80 ? 'Strong' : score >= 60 ? 'Fair' : 'Needs attention'
  const statusClass = score >= 80 ? 'text-green-700 bg-green-50' : score >= 60 ? 'text-yellow-700 bg-yellow-50' : 'text-red-700 bg-red-50'

  const seoMissing = seo
    ? Object.entries(seo).filter(([, value]) => Boolean(value)).map(([key]) => key.replace(/^missing_/, '').replace(/_/g, ' '))
    : []

  return (
    <section className="bg-white border rounded-xl p-5">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Globe size={18} className="text-brand-600" />
            <h2 className="font-semibold">Website intelligence</h2>
          </div>
          <p className="text-xs text-slate-500 break-all">{website}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusClass}`}>{status}</span>
          <div className="text-right">
            <p className="text-xs text-slate-500">Quality</p>
            <p className="text-2xl font-bold text-slate-900">{qualityScore ?? '—'}<span className="text-sm font-medium text-slate-400">/100</span></p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <MiniMetric label="Booking" value={bookingVendor ? formatToken(bookingVendor) : 'Not detected'} positive={Boolean(bookingVendor)} />
        <MiniMetric label="CTA" value={hasCta ? 'Detected' : 'Missing'} positive={Boolean(hasCta)} />
        <MiniMetric label="Contact form" value={hasContactForm ? 'Detected' : 'Missing'} positive={Boolean(hasContactForm)} />
        <MiniMetric label="Social" value={`${socialLinks.length}`} positive={socialLinks.length > 0} />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <EvidenceList title="SEO & mobile" items={[
          `Title: ${seo?.missing_title ? 'missing' : 'present'}`,
          `Description: ${seo?.missing_description ? 'missing' : 'present'}`,
          `H1: ${seo?.missing_h1 ? 'missing' : 'present'}`,
          `Viewport: ${seo?.missing_viewport ? 'missing' : 'present'}`,
          `Favicon: ${seo?.missing_favicon ? 'missing' : 'present'}`,
        ]} />

        <EvidenceList title="Technology" items={[
          `CMS: ${cms.length ? cms.map(formatToken).join(', ') : 'not detected'}`,
          `Analytics: ${analytics.length ? analytics.map(formatToken).join(', ') : 'not detected'}`,
          `Content: ${formatNumber(wordCount)} words`,
          `Scripts: ${formatNumber(scripts)} (${formatNumber(externalScripts)} external)`,
        ]} />

        <EvidenceList title="Accessibility & conversion" items={[
          `Images: ${formatNumber(images)}`,
          `ALT coverage: ${accessibility?.alt_coverage != null ? `${Math.round(Number(accessibility.alt_coverage) * 100)}%` : '—'}`,
          `Forms: ${formatNumber(forms)}`,
          `Booking: ${bookingVendor ? formatToken(bookingVendor) : 'none detected'}`,
        ]} />

        <EvidenceList
          title={weakReasons.length ? 'Why it needs work' : 'Positive signals'}
          items={weakReasons.length ? weakReasons.map(formatToken) : ['No major deterministic weakness detected']}
          warning={weakReasons.length > 0}
        />
      </div>

      {socialLinks.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Social profiles</p>
          <div className="flex flex-wrap gap-2">
            {socialLinks.slice(0, 6).map((link) => (
              <a key={link} href={link} target="_blank" rel="noreferrer" className="text-xs border rounded-full px-2.5 py-1 text-brand-700 hover:bg-brand-50 break-all">
                {shortenUrl(link)}
              </a>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function MiniMetric({ label, value, positive }: { label: string; value: string; positive: boolean }) {
  return (
    <div className="rounded-lg bg-slate-50 border p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <div className="flex items-center gap-1.5">
        {positive ? <CheckCircle2 size={14} className="text-green-600" /> : <XCircle size={14} className="text-slate-400" />}
        <span className="text-sm font-semibold text-slate-800 truncate">{value}</span>
      </div>
    </div>
  )
}

function EvidenceList({ title, items, warning = false }: { title: string; items: string[]; warning?: boolean }) {
  return (
    <div className="border rounded-lg p-3">
      <p className="text-sm font-semibold text-slate-800 mb-2">{title}</p>
      <div className="space-y-1.5">
        {items.map((item, index) => (
          <div key={`${item}-${index}`} className="flex items-start gap-2 text-xs text-slate-600">
            {warning ? <AlertTriangle size={13} className="text-yellow-600 mt-0.5 shrink-0" /> : <CheckCircle2 size={13} className="text-slate-400 mt-0.5 shrink-0" />}
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatToken(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatNumber(value: unknown) {
  if (typeof value === 'number') return value.toLocaleString()
  if (value == null) return '—'
  return String(value)
}

function shortenUrl(value: string) {
  try {
    const url = new URL(value)
    return `${url.hostname}${url.pathname.length > 24 ? `${url.pathname.slice(0, 24)}…` : url.pathname}`
  } catch {
    return value.slice(0, 42)
  }
}

function InsightCard({
  icon,
  label,
  value,
  good = false,
  warning = false,
}: {
  icon: React.ReactNode
  label: string
  value: string
  good?: boolean
  warning?: boolean
}) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">{icon}{label}</div>
      <div className="flex items-center gap-2">
        {good && <CheckCircle2 size={15} className="text-green-600" />}
        {warning && !good && <AlertTriangle size={15} className="text-yellow-600" />}
        {!good && !warning && <XCircle size={15} className="text-slate-400" />}
        <span className="font-semibold text-sm capitalize">{value}</span>
      </div>
    </div>
  )
}

function InfoRow({ label, value, href, icon }: { label: string; value?: string | null; href?: string; icon?: React.ReactNode }) {
  const content = (
    <div className="flex items-start gap-2">
      {icon && <span className="text-slate-400 mt-0.5">{icon}</span>}
      <div className="min-w-0">
        <p className="text-xs text-slate-500 mb-0.5">{label}</p>
        <p className="text-sm font-medium text-slate-800 break-words">{value || '—'}</p>
      </div>
    </div>
  )
  if (!href || !value) return content
  return (
    <a href={href} target={href.startsWith('http') ? '_blank' : undefined} rel={href.startsWith('http') ? 'noreferrer' : undefined} className="hover:text-brand-700">
      {content}
    </a>
  )
}

function CheckItem({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <span className="text-sm text-slate-600">{label}</span>
      {value ? <CheckCircle2 size={17} className="text-green-600" /> : <XCircle size={17} className="text-slate-300" />}
    </div>
  )
}

function ScoreRow({ label, value }: { label: string; value: unknown }) {
  const numeric = typeof value === 'number' ? Math.max(0, Math.min(100, value)) : null
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm capitalize text-slate-600">{label}</span>
        <span className="text-sm font-semibold text-slate-800">{String(value)}</span>
      </div>
      {numeric !== null && (
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-full bg-brand-600 rounded-full" style={{ width: `${numeric}%` }} />
        </div>
      )}
    </div>
  )
}
