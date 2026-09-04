import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

export type ToastVariant = 'success' | 'error' | 'info'

export type ToastItem = {
  id: string
  message: string
  variant: ToastVariant
}

type ToastContextValue = {
  toast: (message: string, variant?: ToastVariant) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const VARIANT_STYLES: Record<
  ToastVariant,
  { wrap: string; icon: typeof CheckCircle2 }
> = {
  success: {
    wrap: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    icon: CheckCircle2,
  },
  error: {
    wrap: 'bg-red-50 border-red-200 text-red-900',
    icon: AlertCircle,
  },
  info: {
    wrap: 'bg-blue-50 border-blue-200 text-blue-900',
    icon: Info,
  },
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      setItems((prev) => [...prev.slice(-4), { id, message, variant }])
      window.setTimeout(() => dismiss(id), 4500)
    },
    [dismiss]
  )

  const value: ToastContextValue = {
    toast,
    success: (m) => toast(m, 'success'),
    error: (m) => toast(m, 'error'),
    info: (m) => toast(m, 'info'),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 max-w-sm w-[calc(100%-2rem)] pointer-events-none"
        aria-live="polite"
        aria-relevant="additions"
      >
        {items.map((item) => {
          const style = VARIANT_STYLES[item.variant]
          const Icon = style.icon
          return (
            <div
              key={item.id}
              role="status"
              className={`pointer-events-auto flex items-start gap-3 border rounded-xl px-4 py-3 shadow-lg text-sm ${style.wrap} animate-toast-in`}
            >
              <Icon size={18} className="shrink-0 mt-0.5" aria-hidden />
              <p className="flex-1 leading-snug">{item.message}</p>
              <button
                type="button"
                onClick={() => dismiss(item.id)}
                className="p-0.5 rounded hover:bg-black/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-current"
                aria-label="Dismiss"
              >
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return ctx
}
