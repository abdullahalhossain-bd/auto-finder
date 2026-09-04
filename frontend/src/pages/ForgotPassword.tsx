import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState<'request' | 'reset'>('request')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const request = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const r = await api.forgotPassword(email)
      setMsg(r.message || 'If registered, a reset was issued.')
      setMode('reset')
    } catch (err: any) {
      setError(err.message)
    }
  }

  const reset = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.resetPassword(token, password)
      setMsg('Password updated. You can log in.')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white border rounded-xl p-6">
        <h1 className="text-xl font-bold mb-4">
          {mode === 'request' ? 'Forgot password' : 'Reset password'}
        </h1>
        {msg && <p className="text-sm text-green-700 mb-3">{msg}</p>}
        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        {mode === 'request' ? (
          <form onSubmit={request} className="space-y-3">
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
            />
            <button type="submit" className="w-full bg-brand-600 text-white py-2 rounded-lg text-sm">
              Send reset
            </button>
          </form>
        ) : (
          <form onSubmit={reset} className="space-y-3">
            <p className="text-xs text-slate-500">
              With ESP_PROVIDER=console, copy the token from API server logs.
            </p>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Reset token"
              required
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password (min 8)"
              required
              minLength={8}
            />
            <button type="submit" className="w-full bg-brand-600 text-white py-2 rounded-lg text-sm">
              Update password
            </button>
          </form>
        )}
        <p className="text-xs text-slate-500 mt-4">
          <Link to="/login" className="underline">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  )
}
