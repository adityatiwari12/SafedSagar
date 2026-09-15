export function ClassificationBadges({
  productType,
  ipType,
  jurisdiction,
}: {
  productType: string
  ipType: string
  jurisdiction: 'india' | 'international'
}) {
  const chips = [
    { label: 'Product', value: productType.replace(/_/g, ' ') },
    { label: 'Need', value: ipType.replace(/_/g, ' ') },
    {
      label: 'Jurisdiction',
      value: jurisdiction === 'india' ? 'India' : 'International',
    },
  ]

  return (
    <ul className="flex flex-wrap gap-2" aria-label="Classification">
      {chips.map((c) => (
        <li
          key={c.label}
          className="rounded-sm border border-surface-border bg-surface-muted px-2.5 py-1 text-xs"
        >
          <span className="font-semibold text-ink-faint">{c.label}: </span>
          <span className="font-semibold capitalize text-navy">{c.value}</span>
        </li>
      ))}
    </ul>
  )
}
