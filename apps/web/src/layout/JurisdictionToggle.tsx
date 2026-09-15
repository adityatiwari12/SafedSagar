export function JurisdictionToggle({
  value,
  onChange,
  disabled,
}: {
  value: 'india' | 'international'
  onChange: (j: 'india' | 'international') => void
  disabled?: boolean
}) {
  return (
    <div
      className="inline-flex overflow-hidden rounded-sm border border-surface-border bg-white"
      role="group"
      aria-label="Jurisdiction"
    >
      <button
        type="button"
        disabled={disabled}
        className={`px-3 py-1.5 text-sm font-semibold ${
          value === 'india' ? 'bg-indiaGreen text-white' : 'text-ink hover:bg-surface-muted'
        }`}
        aria-pressed={value === 'india'}
        onClick={() => onChange('india')}
      >
        India
      </button>
      <button
        type="button"
        disabled={disabled}
        className={`px-3 py-1.5 text-sm font-semibold ${
          value === 'international'
            ? 'bg-primary text-white'
            : 'text-ink hover:bg-surface-muted'
        }`}
        aria-pressed={value === 'international'}
        onClick={() => onChange('international')}
      >
        International
      </button>
    </div>
  )
}
