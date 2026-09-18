import { LANGUAGES, LanguageCode } from '../api/languages'
import { useLanguage } from '../i18n/LanguageContext'

export function LanguageSwitcher({
  value,
  onChange,
  id = 'language-select',
}: {
  value?: LanguageCode
  onChange?: (lang: LanguageCode) => void
  id?: string
}) {
  const ctx = useLanguage()
  const current = value ?? ctx.language
  const handleChange = onChange ?? ctx.setLanguage

  return (
    <div className="flex items-center gap-2 text-sm">
      <label htmlFor={id} className="text-ink-faint">
        {ctx.t('common.language')}
      </label>
      <select
        id={id}
        className="gov-input !w-auto rounded-sm border border-surface-border bg-white px-2 py-1 text-sm font-medium text-ink"
        value={current}
        onChange={(e) => handleChange(e.target.value as LanguageCode)}
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code} lang={lang.code}>
            {lang.nativeName}
          </option>
        ))}
      </select>
    </div>
  )
}
