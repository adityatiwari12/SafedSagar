// Small presentational badges shared between CasesPage (facilitator queue)
// and the Product dossier's Assessments tab, so a case reads the same way
// in both places. Kept plain-string in, not CaseItem['status'] - the
// facilitator queue and the dossier tab only need the visual language, not
// a shared exhaustive-status contract.

const STATUS_STYLES: Record<string, string> = {
  open: 'bg-red-50 text-red-900 border-red-700',
  in_progress: 'bg-amber-100 text-amber-950 border-amber-700',
  awaiting_user_input: 'bg-amber-100 text-amber-950 border-amber-700',
  escalated: 'bg-red-50 text-red-900 border-red-700',
  resolved: 'bg-green-100 text-green-900 border-green-700',
  closed: 'bg-green-100 text-green-900 border-green-700',
}

const RISK_STYLES: Record<string, string> = {
  low: 'bg-green-100 text-green-900 border-green-700',
  medium: 'bg-amber-100 text-amber-950 border-amber-700',
  high: 'bg-red-50 text-red-900 border-red-700',
}

const FALLBACK_STYLE = 'bg-surface-muted text-ink-muted border-line'

const BADGE_CLASS =
  'inline-flex items-center rounded-sm border px-2.5 py-1 text-xs font-bold uppercase tracking-wide'

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`${BADGE_CLASS} ${STATUS_STYLES[status] ?? FALLBACK_STYLE}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export function RiskBadge({ risk }: { risk: string }) {
  return (
    <span className={`${BADGE_CLASS} ${RISK_STYLES[risk] ?? FALLBACK_STYLE}`}>{risk} risk</span>
  )
}
