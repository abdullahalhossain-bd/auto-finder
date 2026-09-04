import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

const EXAMPLES = [
  'Find barber shops in Warsaw, Poland with 50+ reviews that do not have a website. I want to sell them modern websites.',
  'Find dentists in Krakow, Poland with 30+ reviews and no online booking system. I want to offer them an online booking solution.',
  'Find restaurants in Berlin, Germany with 100+ reviews and outdated websites. I want to offer website redesign services.',
]

export default function CreateCampaign() {
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const characterCount = input.length
  const minCharacters = 10

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    const trimmedInput = input.trim()

    if (trimmedInput.length < minCharacters) {
      setError(
        `Please describe your campaign in more detail (at least ${minCharacters} characters).`
      )
      return
    }

    setError('')
    setLoading(true)

    try {
      const campaign = await api.createCampaign(trimmedInput)
      navigate(`/campaigns/${campaign.id}`)
    } catch (err: any) {
      setError(err?.message || 'Failed to create campaign')
    } finally {
      setLoading(false)
    }
  }

  const useExample = (example: string) => {
    setInput(example)
    setError('')
  }

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          Create Campaign
        </h1>

        <p className="text-slate-500 text-sm mt-2 max-w-2xl">
          Tell the AI who you want to find, where they are located, and what
          kind of businesses make a good lead. The system will extract the
          campaign parameters automatically.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-5 flex items-start gap-3 p-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">
          <span className="font-medium">Error:</span>
          <span>{error}</span>
        </div>
      )}

      {/* Main Card */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
        <form onSubmit={handleSubmit}>
          {/* Label */}
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="campaign-description"
              className="text-sm font-semibold text-slate-800"
            >
              Campaign description
            </label>

            <span
              className={`text-xs ${
                characterCount < minCharacters
                  ? 'text-slate-400'
                  : 'text-green-600'
              }`}
            >
              {characterCount} characters
            </span>
          </div>

          {/* Textarea */}
          <textarea
            id="campaign-description"
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              if (error) setError('')
            }}
            rows={8}
            disabled={loading}
            placeholder="Example: Find barber shops in Warsaw, Poland with 50+ reviews that do not have a website or online booking system. I want to sell them modern websites."
            className="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm leading-6 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none disabled:bg-slate-50 disabled:cursor-not-allowed"
          />

          {/* Quick examples */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-700">
                Quick examples
              </p>

              <button
                type="button"
                onClick={() => setInput('')}
                disabled={!input || loading}
                className="text-xs text-slate-400 hover:text-slate-600 disabled:opacity-40"
              >
                Clear
              </button>
            </div>

            <div className="space-y-2">
              {EXAMPLES.map((example, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => useExample(example)}
                  disabled={loading}
                  className="w-full text-left p-3 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 transition text-xs text-slate-600 disabled:opacity-50"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* Buttons */}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={loading || input.trim().length < minCharacters}
              className="bg-brand-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Creating...
                </span>
              ) : (
                'Create Campaign'
              )}
            </button>

            <button
              type="button"
              onClick={() => navigate('/campaigns')}
              disabled={loading}
              className="px-6 py-2.5 rounded-lg text-sm border border-slate-300 hover:bg-slate-50 disabled:opacity-50 transition"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      {/* What to include */}
      <div className="mt-6 bg-slate-50 border border-slate-200 rounded-2xl p-5">
        <h2 className="font-semibold text-slate-800 text-sm mb-4">
          What should you include?
        </h2>

        <div className="grid sm:grid-cols-2 gap-4">
          <Tip
            title="📍 Location"
            text="City, country, region, or specific area."
          />

          <Tip
            title="🏢 Business type"
            text="Barber, dentist, restaurant, gym, lawyer, etc."
          />

          <Tip
            title="🎯 Lead criteria"
            text="Reviews, size, rating, missing website, booking system, etc."
          />

          <Tip
            title="💼 Your offer"
            text="Website, SEO, automation, booking system, marketing, etc."
          />

          <Tip
            title="🔎 Lead quality"
            text="Mention what makes a business a good prospect."
          />

          <Tip
            title="📊 Quantity"
            text="If relevant, specify approximately how many leads you need."
          />
        </div>
      </div>

      {/* Example structure */}
      <div className="mt-6 bg-white border border-slate-200 rounded-2xl p-5">
        <h2 className="font-semibold text-slate-800 text-sm mb-3">
          Recommended structure
        </h2>

        <div className="text-sm text-slate-600 leading-7">
          <p>
            <span className="font-medium text-slate-800">Find:</span>{' '}
            business type
          </p>

          <p>
            <span className="font-medium text-slate-800">Location:</span>{' '}
            city + country
          </p>

          <p>
            <span className="font-medium text-slate-800">Filters:</span>{' '}
            reviews, website, booking system, rating, etc.
          </p>

          <p>
            <span className="font-medium text-slate-800">Offer:</span>{' '}
            what you want to sell
          </p>
        </div>

        <div className="mt-4 p-4 bg-slate-50 rounded-xl text-xs text-slate-600 leading-6">
          <span className="font-semibold text-slate-700">Example:</span>{' '}
          Find dentists in Warsaw, Poland with at least 50 reviews, no online
          booking system, and an outdated website. I want to sell them a modern
          website with online appointment booking. Find up to 50 businesses.
        </div>
      </div>
    </div>
  )
}

function Tip({
  title,
  text,
}: {
  title: string
  text: string
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <p className="text-sm font-medium text-slate-800 mb-1">
        {title}
      </p>

      <p className="text-xs text-slate-500 leading-5">
        {text}
      </p>
    </div>
  )
}