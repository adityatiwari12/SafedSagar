import { LANGUAGES, type LanguageCode } from '../api/languages'
import { useLanguage } from '../i18n/LanguageContext'
import { Link, useLocation } from 'react-router-dom'

/** GIGW-style language picker card — grid of official language names. */
export function LanguageSelectCard({
  id = 'language-select-card',
  compact = false,
}: {
  id?: string
  compact?: boolean
}) {
  const { language, setLanguage, t } = useLanguage()

  return (
    <section
      id={id}
      className={`border border-surface-border bg-white ${compact ? 'p-5' : 'p-6 sm:p-8'}`}
      aria-labelledby={`${id}-title`}
    >
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-saffron/40 pb-4">
        <div>
          <p className="text-xs font-extrabold tracking-[0.16em] text-saffron-deep">
            {t('langCard.title')}
          </p>
          <h2
            id={`${id}-title`}
            className={`mt-1 font-extrabold text-forest ${compact ? 'text-2xl' : 'text-3xl sm:text-4xl'}`}
            lang={language === 'en' ? 'hi' : language}
          >
            {t('langCard.titleHi')}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-ink-muted sm:text-base">{t('langCard.subtitle')}</p>
        </div>
        <p className="text-xs font-semibold text-ink-faint">
          {t('langCard.current')}:{' '}
          <span lang={language} className="font-extrabold text-forest">
            {LANGUAGES.find((l) => l.code === language)?.nativeName}
          </span>
        </p>
      </div>

      <ul className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {LANGUAGES.map((lang) => {
          const active = lang.code === language
          return (
            <li key={lang.code}>
              <button
                type="button"
                lang={lang.code}
                aria-pressed={active}
                onClick={() => setLanguage(lang.code as LanguageCode)}
                className={`flex w-full flex-col items-start border px-3 py-2.5 text-left transition-colors focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-saffron ${
                  active
                    ? 'border-saffron bg-saffron text-white'
                    : 'border-surface-border bg-ivory hover:border-forest hover:bg-white'
                }`}
              >
                <span className={`text-base font-extrabold leading-tight ${active ? 'text-white' : 'text-forest'}`}>
                  {lang.nativeName}
                </span>
                <span className={`mt-0.5 text-[11px] font-semibold ${active ? 'text-white/85' : 'text-ink-faint'}`}>
                  {lang.englishName}
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <p className="mt-4 text-xs text-ink-faint">{t('langCard.hint')}</p>
      <p className="mt-1 text-[11px] font-semibold tracking-wide text-forest-mid">{t('langCard.poweredBy')}</p>
    </section>
  )
}

/** Compact top-bar language control — हिन्दी | English + link to full picker on home. */
export function TopBarLanguageLinks() {
  const { language, setLanguage, t } = useLanguage()
  const location = useLocation()
  const onHome = location.pathname === '/'

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        lang="hi"
        className={`font-hindi hover:underline ${language === 'hi' ? 'font-semibold' : 'opacity-80'}`}
        aria-pressed={language === 'hi'}
        onClick={() => setLanguage('hi')}
      >
        हिन्दी
      </button>
      <span className="opacity-40" aria-hidden="true">
        |
      </span>
      <button
        type="button"
        className={`hover:underline ${language === 'en' ? 'font-semibold' : 'opacity-80'}`}
        aria-pressed={language === 'en'}
        onClick={() => setLanguage('en')}
      >
        English
      </button>
      <span className="opacity-40" aria-hidden="true">
        |
      </span>
      {onHome ? (
        <a href="#language-select-card" className="opacity-90 hover:underline">
          {t('common.language')}
        </a>
      ) : (
        <Link to="/#language-select-card" className="opacity-90 hover:underline">
          {t('common.language')}
        </Link>
      )}
    </div>
  )
}
