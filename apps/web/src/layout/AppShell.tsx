import { Link, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { LanguageCode } from '../api/languages'
import { useLanguage } from '../i18n/LanguageContext'
import { GovTopBar } from './GovTopBar'
import { StateEmblem } from './StateEmblem'
import { LanguageSwitcher } from './LanguageSwitcher'
import { JurisdictionToggle } from './JurisdictionToggle'

export function AppShell({
  children,
  jurisdiction,
  onJurisdictionChange,
  language,
  onLanguageChange,
  showJourneyControls = false,
  chatLayout = false,
  authLayout = false,
}: {
  children: ReactNode
  jurisdiction?: 'india' | 'international'
  onJurisdictionChange?: (j: 'india' | 'international') => void
  language?: LanguageCode
  onLanguageChange?: (l: LanguageCode) => void
  showJourneyControls?: boolean
  chatLayout?: boolean
  /** Compact chrome for login/register — less vertical stretch, slim footer. */
  authLayout?: boolean
}) {
  const { user, status, logout } = useAuth()
  const { t, language: ctxLang } = useLanguage()
  const location = useLocation()

  const crumbMap: Record<string, string> = {
    '/': t('crumbs.home'),
    '/ask': t('crumbs.ask'),
    '/login': t('crumbs.login'),
    '/register': t('crumbs.register'),
    '/placeholder': t('crumbs.placeholder'),
    '/cases': t('crumbs.cases'),
    '/admin': t('crumbs.admin'),
    '/classify': t('crumbs.classify'),
    '/products': t('crumbs.products'),
  }
  const crumb =
    crumbMap[location.pathname] ??
    (location.pathname.startsWith('/products/') ? t('crumbs.productDetail') : t('crumbs.home'))

  const compactChrome = chatLayout || authLayout

  return (
    <div
      className={`flex flex-col ${chatLayout ? 'h-dvh overflow-hidden' : 'min-h-screen'} ${
        authLayout ? 'bg-ivory' : ''
      }`}
      lang={ctxLang}
    >
      <a href="#main-content" className="skip-link">
        {t('common.skipToMain')}
      </a>

      <GovTopBar />

      <div className="tricolor-bar shrink-0" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <header className="shrink-0 border-b border-saffron/70 bg-white">
        <div
          className={`mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 ${
            compactChrome ? 'py-2' : 'py-4'
          }`}
        >
          <div className="flex min-w-0 items-center gap-3">
            <StateEmblem className={`w-auto shrink-0 ${compactChrome ? 'h-9' : 'h-[4.75rem]'}`} />
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-faint sm:text-[11px]">
                {t('common.ministryAyush')} · {t('common.governmentOfIndia')}
              </p>
              <p className="text-[11px] text-ink-muted" lang="hi">
                आयुष मंत्रालय · भारत सरकार
              </p>
              <Link
                to="/"
                className={`block font-bold text-navy hover:text-saffron-deep ${
                  compactChrome ? 'text-base leading-tight' : 'mt-0.5 text-xl sm:text-2xl'
                }`}
              >
                IP-SAKTI Sahayak
              </Link>
              {!compactChrome && (
                <p className="text-sm text-ink-muted">{t('common.portalTagline')}</p>
              )}
              {authLayout && (
                <p className="truncate text-[11px] text-ink-muted">{t('common.portalTagline')}</p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <LanguageSwitcher
              value={language}
              onChange={onLanguageChange}
              id={authLayout ? 'auth-language-select' : 'language-select'}
            />
            {showJourneyControls && jurisdiction && onJurisdictionChange && (
              <JurisdictionToggle value={jurisdiction} onChange={onJurisdictionChange} />
            )}
            {status === 'authenticated' && user && user.role === 'user' && (
              <Link to="/products" className="text-sm font-semibold text-navy hover:text-saffron-deep">
                {t('common.myProducts')}
              </Link>
            )}
            {status === 'authenticated' && user && (
              <div className="flex items-center gap-3 border-l border-surface-border pl-4 text-sm">
                <span className="text-ink-muted">
                  <span className="sr-only">{t('common.signedInAs')} </span>
                  {user.email}
                </span>
                <button type="button" className="gov-btn-secondary !py-1.5" onClick={logout}>
                  {t('common.logout')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {!chatLayout && !authLayout && (
        <nav className="shrink-0 border-b border-surface-border bg-[#f0f4f8]" aria-label="Breadcrumb">
          <div className="mx-auto max-w-6xl px-4 py-2 text-sm text-ink-muted">{crumb}</div>
        </nav>
      )}

      <main
        id="main-content"
        className={
          chatLayout
            ? 'mx-auto flex w-full min-h-0 flex-1 flex-col px-4 py-4'
            : authLayout
              ? 'mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-4 sm:py-5'
              : 'mx-auto w-full max-w-6xl flex-1 px-4 py-6'
        }
      >
        {children}
      </main>

      {chatLayout ? (
        <footer className="shrink-0 border-t-4 border-saffron bg-navy text-white">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-1.5 text-xs text-white/70">
            <span>
              {t('common.governmentOfIndia')} · {t('common.ministryAyush')}
            </span>
            <span>{t('common.copyright')}</span>
          </div>
          <div className="border-t border-white/10 px-4 py-1 text-center text-[10px] text-white/60">
            {t('common.sihStrip')}
          </div>
        </footer>
      ) : authLayout ? (
        <footer className="mt-auto shrink-0 border-t border-surface-border bg-white">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3 text-xs text-ink-muted">
            <span>
              {t('common.governmentOfIndia')} · {t('common.ministryAyush')}
            </span>
            <span>For demonstration purposes</span>
          </div>
          <div className="border-t border-surface-border px-4 py-1 text-center text-[10px] text-ink-faint">
            {t('common.sihStrip')}
          </div>
        </footer>
      ) : (
        <footer className="mt-auto border-t-4 border-saffron bg-navy text-white">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:grid-cols-3">
            <div>
              <div className="flex items-start gap-3">
                <StateEmblem className="h-14 w-auto brightness-0 invert" />
                <div>
                  <p className="font-bold">{t('common.ministryAyush')}</p>
                  <p className="text-sm text-white/80" lang="hi">
                    आयुष मंत्रालय
                  </p>
                  <p className="mt-1 text-sm text-white/80">{t('common.governmentOfIndia')}</p>
                </div>
              </div>
            </div>
            <div className="text-sm">
              <p className="font-semibold">IP-SAKTI Sahayak</p>
              <p className="mt-1 text-white/80">{t('footer.shellBlurb')}</p>
            </div>
            <div className="text-sm">
              <p className="font-semibold">{t('common.important')}</p>
              <p className="mt-1 text-white/80">{t('footer.shellImportant')}</p>
              <p className="mt-3 text-xs text-white/60">{t('footer.gigwNote')}</p>
            </div>
          </div>
          <div className="border-t border-white/15 bg-black/20">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3 text-xs text-white/70">
              <span>{t('common.copyright')}</span>
              <span>{t('common.lastUpdated')}</span>
            </div>
            <div className="border-t border-white/10 px-4 py-1 text-center text-[10px] text-white/60">
              {t('common.sihStrip')}
            </div>
          </div>
          <div className="tricolor-bar" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </footer>
      )}
    </div>
  )
}
