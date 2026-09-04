import { AlertCircle, X } from 'lucide-react'

type ErrorBannerProps = {
  message: string
  onRetry?: () => void
  onDismiss?: () => void
  className?: string
}

export function ErrorBanner({
  message,
  onRetry,
  onDismiss,
  className = '',
}: ErrorBannerProps) {
  if (!message) return null

  return (
    <div
      role="alert"
      className={`mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800 ${className}`}
    >
      <div className="flex items-start gap-2.5 min-w-0">
        <AlertCircle size={18} className="shrink-0 mt-0.5 text-red-600" aria-hidden />
        <span className="break-words">{message}</span>
      </div>
      <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="font-medium text-red-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 rounded"
          >
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="p-1 rounded hover:bg-red-100 text-red-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
          >
            <X size={16} />
          </button>
        )}
      </div>
    </div>
  )
}

type NoticeBannerProps = {
  message: string
  onDismiss?: () => void
  variant?: 'success' | 'info' | 'warning'
}

const variantStyles = {
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-900',
}

export function NoticeBanner({
  message,
  onDismiss,
  variant = 'success',
}: NoticeBannerProps) {
  if (!message) return null
  return (
    <div
      role="status"
      className={`mb-5 flex items-center justify-between gap-3 p-4 border rounded-xl text-sm ${variantStyles[variant]}`}
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="p-1 rounded hover:bg-black/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-current"
        >
          <X size={16} />
        </button>
      )}
    </div>
  )
}
