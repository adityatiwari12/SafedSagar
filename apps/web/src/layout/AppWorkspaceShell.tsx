import { Link, useLocation } from 'react-router-dom'
import { ReactNode, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { LanguageCode } from '../api/languages'
import { useLanguage } from '../i18n/LanguageContext'
import { GovTopBar } from './GovTopBar'
import { StateEmblem } from './StateEmblem'
import { LanguageSwitcher } from './LanguageSwitcher'
import { JurisdictionToggle } from './JurisdictionToggle'
import { groupNav, navForRole } from './navConfig'

/**
 * Authenticated workspace chrome: GoI bar + brand header + role sidebar.
 * Use for all signed-in product surfaces. Login/register keep AppShell authLayout.
 */
export function AppWorkspaceShell({
  children,
  jurisdiction,
  onJurisdictionChange,
  language,
  onLanguageChange,
  showJourneyControls = false,
  dense = false,
}: {
  children: ReactNode
  jurisdiction?: 'india' | 'international'
  onJurisdictionChange?: (j: 'india' | 'international') => void
  language?: LanguageCode
  onLanguageChange?: (l: LanguageCode) => void
  showJourneyControls?: boolean
  /** Full-height content (Ask workspace). */
  dense?: boolean
}) {
  const { user, logout } = useAuth()
  const { t, language: ctxLang } = useLanguage()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)

  const nav = useMemo(
    () => (user ? navForRole(user.role, user.persona) : []),
    [user],
  )
  const grouped = useMemo(() => groupNav(nav), [nav])

  function isActive(to: string) {
    const path = to.split('?')[0]
    if (path === '/dashboard') return location.pathname === '/dashboard'
    if (path === '/products') return location.pathname.startsWith('/products')
    if (path === '/cases') return location.pathname.startsWith('/cases')
    return location.pathname === path || location.pathname.startsWith(`${path}/`)
  }

  return (
    <div
      className={`flex flex-col bg-ivory ${dense ? 'h-dvh overflow-hidden' : 'min-h-screen'}`}
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

      <header className="shrink-0 border-b border-surface-border bg-white">
        <div className="flex items-center justify-between gap-3 px-4 py-2 lg:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="gov-btn-secondary !px-2.5 !py-1.5 lg:hidden"
              aria-expanded={navOpen}
              aria-controls="workspace-sidebar"
              onClick={() => setNavOpen((v) => !v)}
            >
              Menu
            </button>
            <StateEmblem className="h-9 w-auto shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-faint">
                {t('common.ministryAyush')} · {t('common.governmentOfIndia')}
              </p>
              <Link to="/dashboard" className="block truncate text-base font-bold text-navy hover:text-saffron-deep">
                IP-SAKTI Sahayak
              </Link>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="hidden md:block">
              <label htmlFor="workspace-search" className="sr-only">
                Search
              </label>
              <input
                id="workspace-search"
                className="gov-input !w-48 !py-1.5 !text-sm lg:!w-64"
                placeholder="Search workspace…"
                disabled
                title="Global search — coming next"
              />
            </div>
            <LanguageSwitcher
              value={language}
              onChange={onLanguageChange}
              id="workspace-language-select"
            />
            {showJourneyControls && jurisdiction && onJurisdictionChange && (
              <JurisdictionToggle value={jurisdiction} onChange={onJurisdictionChange} />
            )}
            {user && (
              <div className="flex items-center gap-2 border-l border-surface-border pl-3 text-sm">
                <div className="hidden text-right sm:block">
                  <p className="max-w-[10rem] truncate text-xs font-semibold text-ink">{user.email}</p>
                  <p className="text-[10px] uppercase tracking-wide text-ink-faint">
                    {user.role.replace(/_/g, ' ')}
                  </p>
                </div>
                <button type="button" className="gov-btn-secondary !py-1.5 !text-xs" onClick={logout}>
                  {t('common.logout')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside
          id="workspace-sidebar"
          className={`shrink-0 flex-col border-r border-surface-border bg-white ${
            navOpen ? 'fixed inset-y-0 left-0 z-40 flex w-64 pt-[7.5rem] shadow-float lg:static lg:pt-0 lg:shadow-none' : 'hidden lg:flex'
          } lg:w-56 xl:w-60`}
        >
          <nav aria-label="Workspace" className="scroll-thin flex-1 overflow-y-auto px-3 py-4">
            {grouped.map(({ group, items }) => (
              <div key={group} className="mb-5">
                <p className="px-2 text-[10px] font-bold uppercase tracking-[0.14em] text-ink-faint">
                  {group}
                </p>
                <ul className="mt-2 space-y-0.5">
                  {items.map((item) => {
                    const active = isActive(item.to)
                    return (
                      <li key={item.id}>
                        <Link
                          to={item.to}
                          onClick={() => setNavOpen(false)}
                          className={`flex items-center justify-between gap-2 rounded-sm px-2.5 py-2 text-sm font-semibold transition-colors ${
                            active
                              ? 'bg-forest text-white'
                              : 'text-ink hover:bg-ivory'
                          }`}
                        >
                          <span>{item.label}</span>
                          {!item.ready && (
                            <span
                              className={`text-[9px] font-bold uppercase tracking-wide ${
                                active ? 'text-white/70' : 'text-ink-faint'
                              }`}
                            >
                              Soon
                            </span>
                          )}
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))}
          </nav>
          <div className="border-t border-surface-border px-4 py-3 text-[11px] text-ink-faint">
            AI + evidence + human expertise
          </div>
        </aside>

        {navOpen && (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-navy/30 lg:hidden"
            aria-label="Close navigation"
            onClick={() => setNavOpen(false)}
          />
        )}

        <main
          id="main-content"
          className={
            dense
              ? 'flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-3 py-3 sm:px-4'
              : 'min-w-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6'
          }
        >
          {children}
        </main>
      </div>

      {/* CLAUDE.md caveat #4: non-negotiable persistent disclaimer - this
          shell has no other footer, so it's the only place this renders
          for every signed-in workspace page (chat, products, cases, admin). */}
      <footer className="shrink-0 border-t border-surface-border bg-white px-4 py-1 text-center text-[10px] text-ink-faint">
        {t('common.sihStrip')}
      </footer>
    </div>
  )
}
