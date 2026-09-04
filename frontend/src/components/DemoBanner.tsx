import { Link } from 'react-router-dom'

export function DemoBanner() {
  const on =
    localStorage.getItem('demo_mode') === '1' ||
    import.meta.env.VITE_DEMO_MODE === 'true'
  if (!on) return null
  return (
    <div
      className="bg-amber-500 text-amber-950 text-center text-xs sm:text-sm font-medium px-3 py-1.5"
      role="status"
    >
      <strong>DEMO MODE</strong>
      {' — '}
      Demo Data only. Sources like “Google Maps” are simulated labels; no external
      APIs, payments, or AI providers are contacted.{' '}
      <Link to="/demo" className="underline font-semibold">
        Switch demo account
      </Link>
    </div>
  )
}
