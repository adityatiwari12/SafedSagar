import { FormEvent, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { StateEmblem } from '../layout/StateEmblem'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { href: '/', label: 'Home' },
  { href: '#about', label: 'About' },
  { href: '#services', label: 'Services' },
  { href: '#ip-ayurveda', label: 'IP & Ayurveda' },
  { href: '#sources', label: 'Sources' },
  { href: '#faq', label: 'FAQ' },
] as const

export function PortalChrome({ children }: { children: ReactNode }) {
  const { status, logout, user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [q, setQ] = useState('')

  function onSearch(e: FormEvent) {
    e.preventDefault()
    document.getElementById('knowledge')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="flex min-h-screen flex-col bg-ivory">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <div className="bg-navy text-[11px] text-white sm:text-xs">
        <div className="mx-auto flex max-w-portal flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-1 lg:px-8">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span lang="hi" className="font-hindi">
              भारत सरकार
            </span>
            <span className="opacity-40">|</span>
            <span>Government of India</span>
            <span className="opacity-40">|</span>
            <a href="#main-content" className="hover:underline">
              Skip to Main Content
            </a>
            <span className="opacity-40">|</span>
            <span className="opacity-80">Screen Reader Access</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-hindi opacity-80" lang="hi">
              हिन्दी
            </span>
            <span className="font-semibold">English</span>
          </div>
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
                Ministry of Ayush
              </p>
              <p className="text-[11px] text-ink-muted">Government of India</p>
            </div>
          </div>

          <div className="hidden min-w-0 text-center lg:block">
            <Link to="/" className="text-lg font-extrabold tracking-tight text-forest">
              IP-SAKTI Sahayak
            </Link>
            <p className="text-[11px] text-ink-muted">
              Intellectual Property &amp; Regulatory Guidance for Ayurveda
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="gov-btn-secondary !px-3 !py-2 lg:hidden"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              Menu
            </button>
            <Link to="/ask" className="gov-btn-primary !px-4 !py-2 text-sm">
              Ask IP-SAKTI
            </Link>
            {status === 'authenticated' && user && (
              <button type="button" className="hidden text-xs font-semibold text-ink-muted sm:inline" onClick={logout}>
                Logout
              </button>
            )}
          </div>
        </div>

        <div className={`border-t border-surface-border ${menuOpen ? 'block' : 'hidden'} lg:block`}>
          <div className="mx-auto flex max-w-portal flex-col gap-2 px-4 py-1.5 lg:flex-row lg:items-center lg:justify-between lg:px-8">
            <nav aria-label="Primary">
              <ul className="flex flex-col text-[14px] font-semibold text-ink lg:flex-row lg:flex-wrap lg:gap-1">
                {NAV.map((item) => (
                  <li key={item.label}>
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
            <form onSubmit={onSearch} className="hidden md:block">
              <label htmlFor="portal-search" className="sr-only">
                Search knowledge centre
              </label>
              <input
                id="portal-search"
                className="gov-input !w-52 !py-1.5 !text-sm"
                placeholder="Search knowledge centre…"
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
              <p className="font-bold">Ministry of Ayush</p>
              <p className="font-hindi text-sm text-white/75" lang="hi">
                आयुष मंत्रालय
              </p>
              <p className="text-sm text-white/75">Government of India</p>
            </div>
          </div>
          <div className="text-sm">
            <p className="font-bold">Important links</p>
            <ul className="mt-2 space-y-1 text-white/75">
              <li>Ministry of Ayush</li>
              <li>IP India</li>
              <li>WIPO</li>
              <li>National Biodiversity Authority</li>
              <li>FSSAI</li>
            </ul>
          </div>
          <div className="text-sm">
            <p className="font-bold">Portal</p>
            <ul className="mt-2 space-y-1 text-white/75">
              <li>
                <a href="#about" className="hover:underline">
                  About
                </a>
              </li>
              <li>
                <a href="#knowledge" className="hover:underline">
                  Knowledge Centre
                </a>
              </li>
              <li>
                <a href="#faq" className="hover:underline">
                  FAQ
                </a>
              </li>
              <li>
                <a href="#disclaimer" className="hover:underline">
                  Disclaimer
                </a>
              </li>
            </ul>
          </div>
          <div className="text-sm text-white/75">
            <p className="font-bold text-white">Legal</p>
            <ul className="mt-2 space-y-1">
              <li>Accessibility</li>
              <li>Privacy</li>
              <li>Sitemap</li>
            </ul>
            <p className="mt-4 text-xs text-gold-soft">SIH 2026 Prototype</p>
            <p className="text-xs">Not an officially deployed Government of India service unless authorised.</p>
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
