/** Top utility bar matching typical Government of India portals. */
import { useLanguage } from '../i18n/LanguageContext'
import { TopBarLanguageLinks } from '../i18n/LanguageSelectCard'

export function GovTopBar() {
  const { t } = useLanguage()
  return (
    <div className="bg-navy text-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-1.5 text-xs sm:text-sm">
        <p className="font-medium">
          <span lang="hi">भारत सरकार</span>
          <span className="mx-2 text-white/40" aria-hidden="true">
            |
          </span>
          {t('common.governmentOfIndia')}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-white/85">
            <span lang="hi">आयुष मंत्रालय</span>
            <span className="mx-2 text-white/40" aria-hidden="true">
              |
            </span>
            {t('common.ministryAyush')}
          </p>
          <TopBarLanguageLinks />
        </div>
      </div>
    </div>
  )
}
