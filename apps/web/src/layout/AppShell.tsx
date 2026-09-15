import { Link, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { GovTopBar } from './GovTopBar'
import { StateEmblem } from './StateEmblem'
import { LanguageSwitcher } from './LanguageSwitcher'
import { JurisdictionToggle } from './JurisdictionToggle'

const CRUMBS: Record<string, string> = {
  '/': 'Home / IP-SAKTI Sahayak',
  '/login': 'Home / Login',
  '/register': 'Home / Register',
  '/placeholder': 'Home / Role workspace',
}

export function AppShell({
  children,
  jurisdiction,
  onJurisdictionChange,
  language,
  onLanguageChange,
  showJourneyControls = false,
}: {
  children: ReactNode
  jurisdiction?: 'india' | 'international'
  onJurisdictionChange?: (j: 'india' | 'international') => void
  language?: 'en' | 'hi'
  onLanguageChange?: (l: 'en' | 'hi') => void
  showJourneyControls?: boolean
}) {
  const { user, status, logout } = useAuth()
  const location = useLocation()
  const crumb = CRUMBS[location.pathname] ?? 'Home'

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <GovTopBar />

      <div className="tricolor-bar" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <header className="border-b-2 border-saffron/80 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-4">
            <StateEmblem className="h-[4.75rem] w-auto shrink-0" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint sm:text-sm">
                Ministry of Ayush · Government of India
              </p>
              <p className="text-sm font-medium text-ink-muted" lang="hi">
                आयुष मंत्रालय · भारत सरकार
              </p>
              <Link to="/" className="mt-0.5 block text-xl font-bold text-navy hover:text-primary-dark sm:text-2xl">
                IP-SAKTI Sahayak
              </Link>
              <p className="text-sm text-ink-muted">
                Intellectual Property, ABS &amp; Regulatory Guidance for Ayurveda
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            {showJourneyControls && language && onLanguageChange && (
              <LanguageSwitcher value={language} onChange={onLanguageChange} />
            )}
            {showJourneyControls && jurisdiction && onJurisdictionChange && (
              <JurisdictionToggle value={jurisdiction} onChange={onJurisdictionChange} />
            )}
            {status === 'authenticated' && user && (
              <div className="flex items-center gap-3 border-l border-surface-border pl-4 text-sm">
                <span className="text-ink-muted">
                  <span className="sr-only">Signed in as </span>
                  {user.email}
                </span>
                <button type="button" className="gov-btn-secondary !py-1.5" onClick={logout}>
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <nav className="border-b border-surface-border bg-[#f0f4f8]" aria-label="Breadcrumb">
        <div className="mx-auto max-w-6xl px-4 py-2 text-sm text-ink-muted">{crumb}</div>
      </nav>

      <main id="main-content" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {children}
      </main>

      <footer className="mt-auto border-t-4 border-saffron bg-navy text-white">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:grid-cols-3">
          <div>
            <div className="flex items-start gap-3">
              <StateEmblem className="h-14 w-auto brightness-0 invert" />
              <div>
                <p className="font-bold">Ministry of Ayush</p>
                <p className="text-sm text-white/80" lang="hi">
                  आयुष मंत्रालय
                </p>
                <p className="mt-1 text-sm text-white/80">Government of India</p>
              </div>
            </div>
          </div>
          <div className="text-sm">
            <p className="font-semibold">IP-SAKTI Sahayak</p>
            <p className="mt-1 text-white/80">
              Citation-grounded assistance on Ayurveda-related intellectual property,
              biological diversity / ABS, and regulatory pathways (India &amp; international).
            </p>
          </div>
          <div className="text-sm">
            <p className="font-semibold">Important</p>
            <p className="mt-1 text-white/80">
              Guidance on this portal is for information. Confirm filings against official
              gazettes and seek qualified professional advice where required.
            </p>
            <p className="mt-3 text-xs text-white/60">
              Designed to GIGW / UX4G accessibility conventions.
            </p>
          </div>
        </div>
        <div className="border-t border-white/15 bg-black/20">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3 text-xs text-white/70">
            <span>© Ministry of Ayush, Government of India</span>
            <span>Last updated: September 2026</span>
          </div>
        </div>
        <div className="tricolor-bar" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </footer>
    </div>
  )
}
