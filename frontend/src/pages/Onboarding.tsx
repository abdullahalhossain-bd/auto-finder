import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Check,
  ShieldCheck,
  Mail,
  Search,
  ArrowLeft,
  ArrowRight,
  Settings,
  Megaphone,
  X,
} from 'lucide-react'
import { api } from '../lib/api'

const steps = [
  {
    title: 'Safe & compliant outreach',
    description:
      'Use this platform only for legitimate B2B outreach to publicly listed businesses. Every message stays under your control and requires human approval before sending.',
    icon: ShieldCheck,
    badge: 'Step 1',
    bullets: [
      'B2B businesses only',
      'No purchased consumer lists',
      'Human approval required before sending',
      'Do-not-contact protection is enforced',
    ],
  },
  {
    title: 'Set up your sending identity',
    description:
      'Choose the name customers will see when receiving your outreach. You can configure your sending domain and verify SPF/DKIM from Settings.',
    icon: Mail,
    badge: 'Step 2',
    bullets: [
      'Configure your sender name',
      'Use a verified sending domain',
      'SPF and DKIM are required before sending',
      'Sending remains blocked until verification',
    ],
  },
  {
    title: 'Create your first campaign',
    description:
      'Tell the system who you want to find in plain language. Discovery will find businesses, qualify opportunities, and prepare leads for outreach.',
    icon: Search,
    badge: 'Step 3',
    bullets: [
      'Describe a city and country',
      'Specify the business type',
      'Add filters such as no website or no booking',
      'Review qualified leads before outreach',
    ],
  },
]

export default function Onboarding() {
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showSkipConfirm, setShowSkipConfirm] = useState(false)

  const navigate = useNavigate()

  const current = steps[step]
  const Icon = current.icon
  const isLastStep = step === steps.length - 1
  const progress = ((step + 1) / steps.length) * 100

  const next = () => {
    setError('')

    if (!isLastStep) {
      setStep((value) => value + 1)
    }
  }

  const back = () => {
    setError('')

    if (step > 0) {
      setStep((value) => value - 1)
    }
  }

  const finish = async () => {
    setBusy(true)
    setError('')

    try {
      // Best-effort setup.
      // If the backend does not support this yet, onboarding can still continue.
      await api
        .upsertSendingIdentity({
          use_platform_subdomain: true,
          from_name: 'Outreach',
        })
        .catch(() => null)

      localStorage.setItem('onboarding_done', '1')

      // Take the user directly to campaign creation.
      navigate('/campaigns/new')
    } catch (e: unknown) {
      const err = e as { message?: string }
      setError(err.message || 'Unable to finish onboarding')
    } finally {
      setBusy(false)
    }
  }

  const skip = () => {
    localStorage.setItem('onboarding_done', '1')
    navigate('/')
  }

  return (
    <div className="min-h-[calc(100vh-80px)] flex items-center justify-center py-8">
      <div className="w-full max-w-2xl">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-brand-100 text-brand-700 mb-4">
            <Megaphone size={24} />
          </div>

          <h1 className="text-3xl font-bold text-slate-900">
            Welcome to your outreach workspace
          </h1>

          <p className="text-sm text-slate-500 mt-2 max-w-lg mx-auto">
            Let's get your workspace ready in a few quick steps.
          </p>
        </div>

        {/* Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-500">
              {current.badge}
            </span>

            <span className="text-xs font-medium text-slate-500">
              {step + 1} / {steps.length}
            </span>
          </div>

          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="flex justify-between mt-3">
            {steps.map((item, index) => {
              const StepIcon = item.icon
              const completed = index < step
              const active = index === step

              return (
                <div
                  key={item.title}
                  className="flex items-center gap-2"
                >
                  <div
                    className={[
                      'w-7 h-7 rounded-full flex items-center justify-center text-xs',
                      completed
                        ? 'bg-brand-600 text-white'
                        : active
                          ? 'bg-brand-100 text-brand-700'
                          : 'bg-slate-100 text-slate-400',
                    ].join(' ')}
                  >
                    {completed ? (
                      <Check size={14} />
                    ) : (
                      <StepIcon size={14} />
                    )}
                  </div>

                  <span
                    className={[
                      'hidden sm:block text-xs',
                      active
                        ? 'text-slate-900 font-medium'
                        : 'text-slate-400',
                    ].join(' ')}
                  >
                    {item.title}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Main Card */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

          {/* Step Hero */}
          <div className="p-6 sm:p-8 border-b border-slate-100">
            <div className="flex items-start gap-4">
              <div className="shrink-0 w-12 h-12 rounded-xl bg-brand-50 text-brand-700 flex items-center justify-center">
                <Icon size={24} />
              </div>

              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {current.title}
                </h2>

                <p className="text-sm text-slate-600 mt-2 leading-relaxed">
                  {current.description}
                </p>
              </div>
            </div>
          </div>

          {/* Benefits */}
          <div className="p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-4">
              What you get
            </p>

            <div className="space-y-3">
              {current.bullets.map((bullet) => (
                <div
                  key={bullet}
                  className="flex items-start gap-3"
                >
                  <div className="mt-0.5 w-5 h-5 rounded-full bg-green-50 text-green-600 flex items-center justify-center shrink-0">
                    <Check size={13} />
                  </div>

                  <span className="text-sm text-slate-600">
                    {bullet}
                  </span>
                </div>
              ))}
            </div>

            {/* Step-specific information */}
            {step === 1 && (
              <div className="mt-6 p-4 rounded-xl bg-amber-50 border border-amber-100">
                <div className="flex gap-3">
                  <Mail
                    size={18}
                    className="text-amber-700 shrink-0 mt-0.5"
                  />

                  <div>
                    <p className="text-sm font-medium text-amber-900">
                      You can finish this later
                    </p>

                    <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                      Onboarding will prepare a platform sending identity.
                      For real sending, configure and verify your domain from
                      Settings.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="mt-6 p-4 rounded-xl bg-brand-50 border border-brand-100">
                <div className="flex gap-3">
                  <Search
                    size={18}
                    className="text-brand-700 shrink-0 mt-0.5"
                  />

                  <div>
                    <p className="text-sm font-medium text-brand-900">
                      Example campaign
                    </p>

                    <p className="text-xs text-brand-800 mt-1 leading-relaxed">
                      "Find dental clinics in Dhaka with 50+ reviews that do
                      not have a modern website. I want to offer website
                      redesign and online booking."
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="mx-6 sm:mx-8 mb-4 p-3 rounded-lg bg-red-50 border border-red-100 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Footer */}
          <div className="px-6 sm:px-8 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-3">

            <button
              type="button"
              disabled={step === 0 || busy}
              onClick={back}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-white border border-transparent hover:border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ArrowLeft size={16} />
              Back
            </button>

            {isLastStep ? (
              <button
                type="button"
                disabled={busy}
                onClick={finish}
                className="inline-flex items-center gap-2 bg-brand-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Setting up…
                  </>
                ) : (
                  <>
                    Create first campaign
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            ) : (
              <button
                type="button"
                onClick={next}
                className="inline-flex items-center gap-2 bg-brand-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700"
              >
                Continue
                <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Secondary actions */}
        <div className="mt-5 flex items-center justify-center gap-4 text-xs text-slate-400">
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="inline-flex items-center gap-1.5 hover:text-slate-600"
          >
            <Settings size={13} />
            Configure settings
          </button>

          <span>•</span>

          <button
            type="button"
            onClick={() => setShowSkipConfirm(true)}
            className="hover:text-slate-600 underline underline-offset-2"
          >
            Skip for now
          </button>
        </div>
      </div>

      {/* Skip confirmation modal */}
      {showSkipConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">

            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-lg text-slate-900">
                Skip onboarding?
              </h3>

              <button
                type="button"
                onClick={() => setShowSkipConfirm(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-5">
              <p className="text-sm text-slate-600 leading-relaxed">
                You can continue without completing onboarding. You can
                configure your sending identity and other settings later.
              </p>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setShowSkipConfirm(false)}
                  className="px-4 py-2 rounded-lg text-sm border hover:bg-slate-50"
                >
                  Continue setup
                </button>

                <button
                  type="button"
                  onClick={skip}
                  className="px-4 py-2 rounded-lg text-sm bg-slate-800 text-white hover:bg-slate-900"
                >
                  Skip onboarding
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}