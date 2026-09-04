import { Loader2 } from 'lucide-react'

type SpinnerProps = {
  size?: number
  className?: string
  label?: string
}

export function Spinner({
  size = 18,
  className = '',
  label = 'Loading',
}: SpinnerProps) {
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={label}
      className={`inline-flex items-center gap-2 text-slate-500 ${className}`}
    >
      <Loader2 size={size} className="animate-spin shrink-0" aria-hidden />
      {label !== 'Loading' && (
        <span className="text-sm">{label}</span>
      )}
      <span className="sr-only">{label}</span>
    </span>
  )
}
