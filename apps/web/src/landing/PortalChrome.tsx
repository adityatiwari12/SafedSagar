import { FormEvent, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { StateEmblem } from '../layout/StateEmblem'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { TopBarLanguageLinks } from '../i18n/LanguageSelectCard'

const OFFICIAL_LINKS = [
  { label: 'Ministry of Ayush', href: 'https://ayush.gov.in/' },
  { label: 'IP India', href: 'https://www.ipindia.gov.in/' },
  { label: 'WIPO', href: 'https://www.wipo.int/' },
  { label: 'National Biodiversity Authority', href: 'https://nbaindia.org/' },
  { label: 'FSSAI', href: 'https://www.fssai.gov.in/' },
] as const

export function PortalChrome({ children }: { children: ReactNode }) {
  const { status, logout, user } = useAuth()
  const { t, language } = useLanguage()
  const [menuOpen, setMenuOpen] = useState(false)
  const [q, setQ] = useState('')

  const NAV = [
    { href: '/', label: t('nav.home') },
    { href: '#about', label: t('nav.about') },
    { href: '#services', label: t('nav.services') },
    { href: '#ip-ayurveda', label: t('nav.ipAyurveda') },
    { href: '#sources', label: t('nav.sources') },
    { href: '#faq', label: t('nav.faq') },
  ] as const

  function onSearch(e: FormEvent) {
    e.preventDefault()
    const target = document.getElementById('knowledge')
    target?.scrollIntoView({ behavior: 'smooth' })
    if (q.trim()) {
      const cards = target?.querySelectorAll('[data-knowledge-row]')
      cards?.forEach((row) => {
        const el = row as HTMLElement
        const hay = (el.textContent ?? '').toLowerCase()
        el.hidden = !hay.includes(q.trim().toLowerCase())
      })
    } else {
      target?.querySelectorAll('[data-knowledge-row]').forEach((row) => {
        ;(row as HTMLElement).hidden = false
      })
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-ivory" lang={language}>
      <a href="#main-content" className="skip-link">
        {t('common.skipToMain')}
      </a>

      <div className="bg-navy text-[11px] text-white sm:text-xs">
        <div className="mx-auto flex max-w-portal flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-1 lg:px-8">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span lang="hi" className="font-hindi">
              भारत सरकार
            </span>
            <span className="opacity-40">|</span>
            <span>{t('common.governmentOfIndia')}</span>
            <span className="opacity-40">|</span>
            <a href="#main-content" className="hover:underline">
              {t('common.skipToMain')}
            </a>
            <span className="opacity-40">|</span>
            <a href="#disclaimer" className="opacity-90 hover:underline">
              {t('common.screenReader')}
            </a>
          </div>
          <TopBarLanguageLinks />
        </div>
      </div>

      <div className="tricolor-bar" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <header className="sticky top-0 z-50 border-b border-surface-border bg-white">
        <div className="mx-auto flex max-w-portal items-center justify-between gap-4 px-4 py-2 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <StateEmblem className="h-10 w-auto shrink-0 sm:h-11" />
            <div className="min-w-0 leading-tight">
              <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-ink-faint">
                {t('common.ministryAyush')}
              </p>
              <p className="text-[11px] text-ink-muted">{t('common.governmentOfIndia')}</p>
            </div>
          </div>

          <div className="hidden min-w-0 text-center lg:block">
            <Link to="/" className="text-lg font-extrabold tracking-tight text-forest">
              IP-SAKTI Sahayak
            </Link>
            <p className="text-[11px] text-ink-muted">{t('common.portalTagline')}</p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="gov-btn-secondary !px-3 !py-2 lg:hidden"
              aria-expanded={menuOpen}
              aria-controls="portal-primary-nav"
              onClick={() => setMenuOpen((v) => !v)}
            >
              {t('common.menu')}
            </button>
            {status !== 'authenticated' && (
              <Link to="/login" className="hidden text-sm font-semibold text-forest sm:inline hover:underline">
                {t('common.login')}
              </Link>
            )}
            <Link to="/ask" className="gov-btn-primary !px-4 !py-2 text-sm">
              {t('common.askIpsakti')}
            </Link>
            {status === 'authenticated' && user && (
              <button type="button" className="hidden text-xs font-semibold text-ink-muted sm:inline" onClick={logout}>
                {t('common.logout')}
              </button>
            )}
          </div>
        </div>

        <div
          id="portal-primary-nav"
          className={`border-t border-surface-border ${menuOpen ? 'block' : 'hidden'} lg:block`}
        >
          <div className="mx-auto flex max-w-portal flex-col gap-2 px-4 py-1.5 lg:flex-row lg:items-center lg:justify-between lg:px-8">
            <nav aria-label={t('nav.primary')}>
              <ul className="flex flex-col text-[14px] font-semibold text-ink lg:flex-row lg:flex-wrap lg:gap-1">
                {NAV.map((item) => (
                  <li key={item.href}>
                    {item.href.startsWith('#') ? (
                      <a
                        href={item.href}
                        className="block px-2.5 py-1.5 hover:text-saffron-deep"
                        onClick={() => setMenuOpen(false)}
                      >
                        {item.label}
                      </a>
                    ) : (
                      <Link
                        to={item.href}
                        className="block px-2.5 py-1.5 hover:text-saffron-deep"
                        onClick={() => setMenuOpen(false)}
                      >
                        {item.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </nav>
            <form onSubmit={onSearch} className="block">
              <label htmlFor="portal-search" className="sr-only">
                {t('common.searchLabel')}
              </label>
              <input
                id="portal-search"
                className="gov-input !w-full !py-1.5 !text-sm md:!w-52"
                placeholder={t('common.searchPlaceholder')}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </form>
          </div>
        </div>
      </header>

      <main id="main-content" className="flex-1">
        {children}
      </main>

      <footer className="border-t-4 border-saffron bg-navy text-white">
        <div className="mx-auto grid max-w-portal gap-8 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4 lg:px-8">
          <div className="flex gap-3">
            <StateEmblem className="h-12 w-auto brightness-0 invert" />
            <div>
              <p className="font-bold">{t('common.ministryAyush')}</p>
              <p className="font-hindi text-sm text-white/75" lang="hi">
                आयुष मंत्रालय
              </p>
              <p className="text-sm text-white/75">{t('common.governmentOfIndia')}</p>
            </div>
          </div>
          <div className="text-sm">
            <p className="font-bold">{t('footer.importantLinks')}</p>
            <ul className="mt-2 space-y-1 text-white/75">
              {OFFICIAL_LINKS.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div className="text-sm">
            <p className="font-bold">{t('footer.portal')}</p>
            <ul className="mt-2 space-y-1 text-white/75">
              <li>
                <a href="#about" className="hover:underline">
                  {t('footer.about')}
                </a>
              </li>
              <li>
                <a href="#knowledge" className="hover:underline">
                  {t('footer.knowledgeCentre')}
                </a>
              </li>
              <li>
                <a href="#faq" className="hover:underline">
                  {t('footer.faq')}
                </a>
              </li>
              <li>
                <a href="#disclaimer" className="hover:underline">
                  {t('footer.disclaimer')}
                </a>
              </li>
            </ul>
          </div>
          <div className="text-sm text-white/75">
            <p className="font-bold text-white">{t('footer.legal')}</p>
            <ul className="mt-2 space-y-1">
              <li>
                <a href="#disclaimer" className="hover:underline">
                  {t('common.accessibility')}
                </a>
              </li>
              <li>
                <a href="#disclaimer" className="hover:underline">
                  {t('common.privacy')}
                </a>
              </li>
              <li>
                <a href="#about" className="hover:underline">
                  {t('common.sitemap')}
                </a>
              </li>
            </ul>
            <p className="mt-4 text-xs text-gold-soft">{t('footer.notOfficial')}</p>
          </div>
        </div>
        <div className="border-t border-white/10 px-4 py-1 text-center text-[10px] text-white/60">
          {t('common.sihStrip')}
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
