import { FormEvent, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth, ApiError } from '../auth/AuthContext'
import { AppShell } from '../layout/AppShell'

export default function LoginPage() {
  const { login, status, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (status === 'authenticated' && user) {
    return <Navigate to={user.role === 'user' ? '/' : '/placeholder'} replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-md">
        <h1 className="text-2xl font-bold text-navy">Login</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Sign in to IP-SAKTI Sahayak (Ministry of Ayush). New users can register in under a
          minute.
        </p>

        <form onSubmit={onSubmit} className="gov-panel mt-6 space-y-4 p-5">
          <div>
            <label className="gov-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              className="gov-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="gov-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="gov-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {error && (
            <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="gov-btn-primary w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Login'}
          </button>
        </form>

        <p className="mt-4 text-sm text-ink-muted">
          No account?{' '}
          <Link to="/register" className="font-semibold text-primary underline">
            Register
          </Link>
        </p>
      </div>
    </AppShell>
  )
}
