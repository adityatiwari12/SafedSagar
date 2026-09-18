import { FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth, ApiError } from '../auth/AuthContext'
import { AppShell } from '../layout/AppShell'
import { roleHomePath } from '../auth/roleHome'
import { useLanguage } from '../i18n/LanguageContext'

const DEMO_PASSWORD = 'DemoPass123!'

const DEMO_ACCOUNTS = [
  {
    label: 'AYUSH User',
    email: 'demo-user@ipsakti.demo',
    description: 'Product, IP & compliance guidance',
    icon: 'user' as const,
  },
  {
    label: 'IP Facilitator',
    email: 'demo-facilitator@ipsakti.demo',
    description: 'Case review & expert coordination',
    icon: 'facilitator' as const,
  },
  {
    label: 'Regulatory Expert',
    email: 'demo-regulatory-expert@ipsakti.demo',
    description: 'Compliance & regulatory review',
    icon: 'expert' as const,
  },
  {
    label: 'Admin',
    email: 'demo-admin@ipsakti.demo',
    description: 'Platform & knowledge-base management',
    icon: 'admin' as const,
  },
]

type LoginNavState = {
  from?: string
  prefill?: string
  seededDraft?: string
  activeProduct?: { id: string; name: string }
} | null

function RoleIcon({ kind }: { kind: (typeof DEMO_ACCOUNTS)[number]['icon'] }) {
  const common = 'h-4 w-4 shrink-0 text-forest'
  if (kind === 'user') {
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 20a8 8 0 0 1 16 0"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
        />
      </svg>
    )
  }
  if (kind === 'facilitator') {
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M9 12h6M12 9v6M4 7h16v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Z"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M8 7V5a4 4 0 0 1 8 0v2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      </svg>
    )
  }
  if (kind === 'expert') {
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 3 4 7v5c0 5 3.4 9.4 8 10 4.6-.6 8-5 8-10V7l-8-4Z"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
        <path d="m9.5 12 1.8 1.8 3.7-3.8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      </svg>
    )
  }
  return (
    <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M19.4 15a7.7 7.7 0 0 0 .1-1l2-1.2-2-3.4-2.3.6a7.6 7.6 0 0 0-1.7-1L15 6h-4l-.5 2.5a7.6 7.6 0 0 0-1.7 1l-2.3-.6-2 3.4 2 1.2a7.7 7.7 0 0 0 0 2l-2 1.2 2 3.4 2.3-.6a7.6 7.6 0 0 0 1.7 1L11 22h4l.5-2.5a7.6 7.6 0 0 0 1.7-1l2.3.6 2-3.4-2-1.2Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function BotanicalPattern({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 420 480"
      fill="none"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="210" cy="240" r="150" stroke="currentColor" strokeOpacity="0.12" strokeWidth="1" />
      <circle cx="210" cy="240" r="100" stroke="currentColor" strokeOpacity="0.16" strokeWidth="1" />
      <path
        d="M210 80c20 50 20 110 0 160-20-50-20-110 0-160Z"
        fill="currentColor"
        fillOpacity="0.08"
      />
      <path
        d="M210 80c-20 50-20 110 0 160 20-50 20-110 0-160Z"
        fill="currentColor"
        fillOpacity="0.08"
      />
      <path
        d="M110 200c60 10 110 50 140 100-60-10-110-50-140-100Z"
        fill="currentColor"
        fillOpacity="0.07"
      />
      <path
        d="M310 200c-60 10-110 50-140 100 60-10 110-50 140-100Z"
        fill="currentColor"
        fillOpacity="0.07"
      />
      <circle cx="210" cy="240" r="6" fill="currentColor" fillOpacity="0.25" />
      <path
        d="M70 360h280M90 390h240"
        stroke="currentColor"
        strokeOpacity="0.1"
        strokeWidth="1"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function LoginPage() {
  const { login, status, user } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const navState = (location.state as LoginNavState) ?? null
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [forgotHint, setForgotHint] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function resumeAfterLogin(role: Parameters<typeof roleHomePath>[0]) {
    const draft = navState?.prefill ?? navState?.seededDraft
    if (navState?.from?.startsWith('/ask') || draft || navState?.activeProduct) {
      navigate('/ask', {
        replace: true,
        state: {
          seededDraft: draft,
          activeProduct: navState?.activeProduct,
        },
      })
      return
    }
    if (navState?.from && navState.from !== '/login' && navState.from !== '/register') {
      navigate(navState.from, { replace: true })
      return
    }
    navigate(roleHomePath(role), { replace: true })
  }

  if (status === 'authenticated' && user) {
    const draft = navState?.prefill ?? navState?.seededDraft
    if (navState?.from?.startsWith('/ask') || draft || navState?.activeProduct) {
      return (
        <Navigate
          to="/ask"
          replace
          state={{ seededDraft: draft, activeProduct: navState?.activeProduct }}
        />
      )
    }
    if (navState?.from && navState.from !== '/login' && navState.from !== '/register') {
      return <Navigate to={navState.from} replace />
    }
    return <Navigate to={roleHomePath(user.role)} replace />
  }

  async function doLogin(loginEmail: string, loginPassword: string) {
    setBusy(true)
    setError(null)
    try {
      const profile = await login(loginEmail.trim(), loginPassword)
      resumeAfterLogin(profile.role)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    await doLogin(email, password)
  }

  function fillDemoAccount(demoEmail: string) {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
  }

  async function quickLogin(demoEmail: string) {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
    await doLogin(demoEmail, DEMO_PASSWORD)
  }

  return (
    <AppShell authLayout>
      <div className="flex flex-1 flex-col justify-center">
        <div className="grid overflow-hidden rounded-md border border-surface-border bg-white shadow-panel lg:grid-cols-2 lg:shadow-float">
          {/* Brand panel */}
          <aside className="relative overflow-hidden bg-forest px-6 py-8 text-white sm:px-8 lg:px-10 lg:py-10">
            <BotanicalPattern className="pointer-events-none absolute -right-8 bottom-0 h-[70%] w-auto text-gold-soft opacity-90" />
            <div className="relative max-w-md">
              <p className="text-[11px] font-bold tracking-[0.16em] text-gold-soft">IP-SAKTI SAHAYAK</p>
              <h1 className="mt-3 text-2xl font-extrabold leading-snug tracking-tight sm:text-[1.75rem]">
                Welcome to IP-SAKTI Sahayak
              </h1>
              <p className="mt-3 text-sm leading-relaxed text-white/85 sm:text-[15px]">
                Your AI-assisted gateway for Ayurveda intellectual property and regulatory guidance.
              </p>
              <p className="mt-2 text-xs leading-relaxed text-white/65 sm:text-sm">
                Access source-cited guidance across IP, regulatory, traditional knowledge and
                biodiversity frameworks.
              </p>

              <ul className="mt-7 space-y-3 text-sm text-white/90">
                {[
                  'Source-cited AI guidance',
                  'India & International IP intelligence',
                  'Human expert assistance',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-saffron"
                      aria-hidden="true"
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>

              <p className="mt-8 text-[11px] font-semibold uppercase tracking-[0.14em] text-white/50">
                {t('common.portalTagline')}
              </p>
            </div>
          </aside>

          {/* Auth panel */}
          <div className="flex flex-col justify-center px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
            <div>
              <h2 className="text-xl font-extrabold text-navy sm:text-2xl">
                Sign in to IP-SAKTI Sahayak
              </h2>
              <p className="mt-1.5 text-sm text-ink-muted">
                Use your registered account to continue securely.
              </p>
            </div>

            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div>
                <label className="gov-label" htmlFor="email">
                  {t('auth.email')}
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  className="gov-input !py-2.5"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <label className="gov-label !mb-0" htmlFor="password">
                    {t('auth.password')}
                  </label>
                  <button
                    type="button"
                    className="text-xs font-semibold text-forest hover:text-saffron-deep hover:underline"
                    onClick={() => setForgotHint((v) => !v)}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    className="gov-input !py-2.5 !pr-11"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-ink-faint hover:text-forest"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path
                          d="M3 3l18 18M10.5 10.6a2.5 2.5 0 0 0 3 3M9.2 5.4A10.4 10.4 0 0 1 12 5c5 0 9.3 3.1 11 7.5a12.3 12.3 0 0 1-4.1 5.1M6.1 6.1A12.2 12.2 0 0 0 1 12.5C2.7 16.9 7 20 12 20c1.7 0 3.3-.3 4.8-1"
                          stroke="currentColor"
                          strokeWidth="1.75"
                          strokeLinecap="round"
                        />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path
                          d="M1 12.5C2.7 8.1 7 5 12 5s9.3 3.1 11 7.5C21.3 16.9 17 20 12 20S2.7 16.9 1 12.5Z"
                          stroke="currentColor"
                          strokeWidth="1.75"
                        />
                        <circle cx="12" cy="12.5" r="3" stroke="currentColor" strokeWidth="1.75" />
                      </svg>
                    )}
                  </button>
                </div>
                {forgotHint && (
                  <p className="mt-2 text-xs text-ink-muted" role="status">
                    Password reset is not enabled in this demonstration. Use Explore Demo below or
                    register a new account.
                  </p>
                )}
              </div>

              {error && (
                <p className="rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
                  {error}
                </p>
              )}

              <button
                type="submit"
                className="gov-btn-primary w-full !py-3 text-base"
                disabled={busy}
              >
                {busy ? `${t('auth.submit')}…` : t('auth.submit')}
              </button>
            </form>

            <p className="mt-4 text-center text-sm text-ink-muted">
              {t('auth.noAccount')}{' '}
              <Link
                to="/register"
                state={navState}
                className="font-semibold text-forest underline-offset-2 hover:text-saffron-deep hover:underline"
              >
                {t('auth.registerLink')}
              </Link>
            </p>

            <div className="my-6 flex items-center gap-3" aria-hidden="true">
              <span className="h-px flex-1 bg-surface-border" />
              <span className="text-[11px] font-bold tracking-[0.14em] text-ink-faint">OR</span>
              <span className="h-px flex-1 bg-surface-border" />
            </div>

            <section
              className="rounded-sm border border-dashed border-surface-border bg-ivory/80 p-4"
              aria-labelledby="demo-explore-heading"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 id="demo-explore-heading" className="text-sm font-bold text-forest">
                    Explore the platform
                  </h3>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    Use a demo role to experience the IP-SAKTI workflow. Not for production use.
                  </p>
                </div>
                <span className="rounded-sm bg-white px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-ink-faint ring-1 ring-surface-border">
                  Demo only
                </span>
              </div>

              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {DEMO_ACCOUNTS.map((acct) => (
                  <li key={acct.email}>
                    <button
                      type="button"
                      onClick={() => quickLogin(acct.email)}
                      onDoubleClick={() => fillDemoAccount(acct.email)}
                      disabled={busy}
                      title={`${acct.email} — click to sign in`}
                      className="flex w-full items-start gap-2.5 rounded-sm border border-surface-border bg-white px-3 py-2.5 text-left transition-colors hover:border-forest/40 hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-saffron disabled:opacity-60"
                    >
                      <span className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-sm bg-ayush-soft">
                        <RoleIcon kind={acct.icon} />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-bold text-navy">{acct.label}</span>
                        <span className="mt-0.5 block text-[11px] leading-snug text-ink-muted">
                          {acct.description}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
