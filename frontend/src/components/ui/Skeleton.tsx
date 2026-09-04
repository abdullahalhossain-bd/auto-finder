type SkeletonProps = {
  className?: string
}

/** Generic pulse block for loading placeholders */
export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`bg-slate-200/80 rounded animate-pulse ${className}`}
      aria-hidden
    />
  )
}

/** Full-page style skeleton used while primary data loads */
export function PageSkeleton({
  rows = 4,
  withHeader = true,
}: {
  rows?: number
  withHeader?: boolean
}) {
  return (
    <div className="space-y-6" role="status" aria-label="Loading content">
      {withHeader && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-2">
            <Skeleton className="h-7 w-40 sm:w-48" />
            <Skeleton className="h-4 w-64 sm:w-80 max-w-full" />
          </div>
          <Skeleton className="h-10 w-28 rounded-lg" />
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-white border border-slate-200 rounded-xl p-4 space-y-3"
          >
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-8 w-16" />
          </div>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="h-12 bg-slate-50 border-b border-slate-200" />
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="h-16 sm:h-20 border-b border-slate-100 flex items-center gap-4 px-4 sm:px-5"
          >
            <Skeleton className="h-4 w-1/3 max-w-xs" />
            <Skeleton className="h-6 w-16 rounded-full hidden sm:block" />
            <Skeleton className="h-4 w-12 ml-auto" />
          </div>
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  )
}

/** Card list skeleton (approvals, inbox, etc.) */
export function CardListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4" role="status" aria-label="Loading list">
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-72 max-w-full" />
      </div>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-white border border-slate-200 rounded-xl p-5 space-y-3"
        >
          <div className="flex justify-between gap-3">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="flex gap-2 pt-2">
            <Skeleton className="h-9 w-24 rounded-lg" />
            <Skeleton className="h-9 w-24 rounded-lg" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}
