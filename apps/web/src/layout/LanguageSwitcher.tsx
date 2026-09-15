import { LANGUAGES, LanguageCode } from '../api/languages'

export function LanguageSwitcher({
  value,
  onChange,
}: {
  value: LanguageCode
  onChange: (lang: LanguageCode) => void
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <label htmlFor="language-select" className="text-ink-faint">
        Language
      </label>
      <select
        id="language-select"
        className="gov-input !w-auto rounded-sm border border-surface-border bg-white px-2 py-1 text-sm font-medium text-ink"
        value={value}
        onChange={(e) => onChange(e.target.value as LanguageCode)}
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
