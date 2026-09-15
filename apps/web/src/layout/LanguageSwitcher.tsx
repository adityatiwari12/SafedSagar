type Language = 'en' | 'hi'

export function LanguageSwitcher({
  value,
  onChange,
}: {
  value: Language
  onChange: (lang: Language) => void
}) {
  return (
    <div className="flex items-center gap-2 text-sm" role="group" aria-label="Language">
      <span className="text-ink-faint">Language</span>
      <button
        type="button"
        className={`rounded-sm px-2 py-1 font-medium ${
          value === 'en' ? 'bg-primary text-white' : 'bg-white text-ink hover:bg-surface-muted'
        }`}
        aria-pressed={value === 'en'}
        onClick={() => onChange('en')}
      >
        English
      </button>
      <button
        type="button"
        className="cursor-not-allowed rounded-sm border border-dashed border-surface-border px-2 py-1 text-ink-faint"
        title="Hindi coming in a later phase (Bhashini)"
        aria-disabled="true"
        disabled
      >
        हिंदी
      </button>
    </div>
  )
}
