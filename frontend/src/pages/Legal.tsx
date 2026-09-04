import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  FileText,
  ShieldCheck,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'

const titles: Record<string, string> = {
  privacy: 'Privacy Policy',
  terms: 'Terms of Service',
}

const descriptions: Record<string, string> = {
  privacy:
    'Learn how we collect, use, protect, and manage your information when you use our service.',
  terms:
    'The rules and conditions that apply when you access or use our service.',
}

export default function Legal() {
  const { doc } = useParams<{ doc: string }>()

  const key = doc === 'terms' ? 'terms' : 'privacy'
  const title = titles[key]
  const description = descriptions[key]

  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadDocument = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`/api/v1/legal/${key}`, {
        headers: {
          Accept: 'text/plain',
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to load ${title}`)
      }

      const content = await response.text()

      if (!content.trim()) {
        throw new Error('The document is empty.')
      }

      setText(content)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setError(e.message || 'Unable to load this document.')
      setText('')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDocument()
  }, [key])

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-4xl mx-auto px-4 py-8 sm:py-12">

        {/* Back */}
        <Link
          to="/login"
          className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors mb-8"
        >
          <ArrowLeft size={16} />
          Back to login
        </Link>

        {/* Header */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 mb-5 shadow-sm">
          <div className="flex items-start gap-4">

            <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-700 flex items-center justify-center shrink-0">
              {key === 'privacy' ? (
                <ShieldCheck size={24} />
              ) : (
                <FileText size={24} />
              )}
            </div>

            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">
                {title}
              </h1>

              <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                {description}
              </p>
            </div>
          </div>
        </div>

        {/* Document */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

          {loading && (
            <div className="p-10 flex flex-col items-center justify-center text-center">
              <div className="w-9 h-9 border-2 border-slate-200 border-t-brand-600 rounded-full animate-spin mb-4" />

              <p className="text-sm font-medium text-slate-700">
                Loading document…
              </p>

              <p className="text-xs text-slate-400 mt-1">
                Please wait a moment.
              </p>
            </div>
          )}

          {!loading && error && (
            <div className="p-8 sm:p-10 text-center">
              <div className="w-12 h-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto mb-4">
                <AlertCircle size={24} />
              </div>

              <h2 className="font-semibold text-slate-900 mb-1">
                Unable to load document
              </h2>

              <p className="text-sm text-slate-500 mb-5">
                {error}
              </p>

              <button
                type="button"
                onClick={loadDocument}
                className="inline-flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
              >
                <RefreshCw size={15} />
                Try again
              </button>
            </div>
          )}

          {!loading && !error && text && (
            <>
              <div className="px-6 sm:px-10 py-8 sm:py-10">
                <article
                  className="
                    whitespace-pre-wrap
                    break-words
                    text-sm
                    sm:text-[15px]
                    text-slate-700
                    font-sans
                    leading-7
                  "
                >
                  {text}
                </article>
              </div>

              {/* Footer */}
              <div className="border-t border-slate-100 bg-slate-50 px-6 sm:px-10 py-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <p className="text-xs text-slate-400">
                    Please review this document carefully before using the
                    service.
                  </p>

                  <button
                    type="button"
                    onClick={loadDocument}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800"
                  >
                    <RefreshCw size={13} />
                    Reload
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-center gap-4 mt-6 text-xs text-slate-400">
          {key === 'privacy' ? (
            <Link
              to="/legal/terms"
              className="hover:text-slate-700 hover:underline"
            >
              Terms of Service
            </Link>
          ) : (
            <Link
              to="/legal/privacy"
              className="hover:text-slate-700 hover:underline"
            >
              Privacy Policy
            </Link>
          )}

          <span>•</span>

          <Link
            to="/login"
            className="hover:text-slate-700 hover:underline"
          >
            Login
          </Link>
        </div>
      </div>
    </div>
  )
}