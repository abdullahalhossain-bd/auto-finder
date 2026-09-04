export function scoreTier(score?: number | null) {
  if (score == null) return { tier: 'unqualified', label: 'Unqualified', className: 'bg-slate-100 text-slate-600' }
  if (score >= 80) return { tier: 'hot', label: 'Hot Lead', className: 'bg-red-50 text-red-700' }
  if (score >= 65) return { tier: 'qualified', label: 'Qualified', className: 'bg-emerald-50 text-emerald-700' }
  if (score >= 45) return { tier: 'medium', label: 'Medium', className: 'bg-amber-50 text-amber-800' }
  if (score >= 25) return { tier: 'low', label: 'Low', className: 'bg-slate-100 text-slate-600' }
  return { tier: 'unqualified', label: 'Unqualified', className: 'bg-slate-100 text-slate-500' }
}

export function ScoreBadge({ score }: { score?: number | null }) {
  const t = scoreTier(score)
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${t.className}`}
      title={t.label}
    >
      {score != null ? `${Math.round(score)}/100` : '—'} · {t.label}
    </span>
  )
}
