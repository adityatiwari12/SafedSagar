import { FormEvent, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth, ApiError } from '../auth/AuthContext'
import { AppShell } from '../layout/AppShell'
import { SelfRegisterableRole, UserPersona } from '../api/authApi'

const ROLE_OPTIONS: { value: SelfRegisterableRole; label: string; hint: string }[] = [
  {
    value: 'user',
    label: 'User',
    hint: 'Practitioners, researchers, AYUSH startups/MSMEs, cultivators — ask questions right away.',
  },
  {
    value: 'facilitator',
    label: 'IP Facilitator (request access)',
    hint: 'Reviews escalated IP cases. Requires admin verification before your dashboard activates.',
  },
  {
    value: 'regulatory_expert',
    label: 'Regulatory Expert (request access)',
    hint: 'Reviews escalated regulatory-compliance cases. Requires admin verification before activation.',
  },
]

const PERSONA_OPTIONS: { value: UserPersona; label: string }[] = [
  { value: 'entrepreneur', label: 'AYUSH Entrepreneur / MSME' },
  { value: 'practitioner_researcher', label: 'Practitioner / Researcher' },
  { value: 'cultivator', label: 'Cultivator / Biological Resource Provider' },
]

export default function RegisterPage() {
  const { register, status, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<SelfRegisterableRole>('user')
  const [persona, setPersona] = useState<UserPersona>('entrepreneur')
  const [consentPrivacy, setConsentPrivacy] = useState(false)
  const [consentTerms, setConsentTerms] = useState(false)
  const [consentNotAdvice, setConsentNotAdvice] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (status === 'authenticated' && user) {
    return <Navigate to={user.role === 'user' ? '/ask' : '/placeholder'} replace />
  }

  const allConsentsGiven = consentPrivacy && consentTerms && consentNotAdvice
  const requestsVerification = role !== 'user'

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!allConsentsGiven) {
      setError('Please accept all three acknowledgements below to continue.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await register(email.trim(), password, {
        role,
        ...(role === 'user' ? { persona } : {}),
      })
      navigate(requestsVerification ? '/placeholder' : '/ask')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-md">
        <h1 className="text-2xl font-bold text-navy">Register</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Create an account for practitioners, researchers, AYUSH startups / MSMEs or
          cultivators. Password must be 8–72 characters.
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
              autoComplete="new-password"
              className="gov-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              maxLength={72}
            />
            <p className="mt-1 text-xs text-ink-faint">Use at least 8 characters (max 72).</p>
          </div>

          <fieldset>
            <legend className="gov-label">I am registering as</legend>
            <div className="mt-2 space-y-2">
              {ROLE_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className="flex cursor-pointer items-start gap-2 rounded-sm border border-line p-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                >
                  <input
                    type="radio"
                    name="role"
                    value={opt.value}
                    checked={role === opt.value}
                    onChange={() => setRole(opt.value)}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block font-semibold text-navy">{opt.label}</span>
                    <span className="block text-xs text-ink-muted">{opt.hint}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          {role === 'user' && (
            <div>
              <label className="gov-label" htmlFor="persona">
                Which best describes you?
              </label>
              <select
                id="persona"
                className="gov-input"
                value={persona}
                onChange={(e) => setPersona(e.target.value as UserPersona)}
              >
                {PERSONA_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-ink-faint">
                Used only to tailor your dashboard — all users get the same access.
              </p>
            </div>
          )}

          {requestsVerification && (
            <p className="rounded-sm bg-amber-50 px-3 py-2 text-xs text-amber-900">
              This role requires admin verification. Your account will be created, but the
              facilitator/expert workspace stays locked until an administrator approves your
              request.
            </p>
          )}

          <div className="space-y-2 border-t border-line pt-3">
            <label className="flex items-start gap-2 text-xs text-ink-muted">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={consentPrivacy}
                onChange={(e) => setConsentPrivacy(e.target.checked)}
                required
              />
              I have read and accept the Privacy Policy.
            </label>
            <label className="flex items-start gap-2 text-xs text-ink-muted">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={consentTerms}
                onChange={(e) => setConsentTerms(e.target.checked)}
                required
              />
              I have read and accept the Terms of Use.
            </label>
            <label className="flex items-start gap-2 text-xs text-ink-muted">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={consentNotAdvice}
                onChange={(e) => setConsentNotAdvice(e.target.checked)}
                required
              />
              I understand this assistant provides information, not legal advice.
            </label>
          </div>

          {error && (
            <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="gov-btn-primary w-full" disabled={busy}>
            {busy ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="mt-4 text-sm text-ink-muted">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-primary underline">
            Login
          </Link>
        </p>
      </div>
    </AppShell>
  )
}
