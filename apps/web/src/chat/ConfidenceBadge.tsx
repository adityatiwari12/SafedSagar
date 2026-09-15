import { ChatTurnResponse } from '../api/chatApi'

const BAND_STYLES = {
  high: 'bg-green-100 text-green-900 border-green-700',
  medium: 'bg-amber-100 text-amber-950 border-amber-700',
  low: 'bg-red-50 text-red-900 border-red-700',
} as const

export function ConfidenceBadge({
  band,
  confidence,
}: {
  band: ChatTurnResponse['confidence_band']
  confidence: number
}) {
  const pct = Math.round(confidence * 100)
  return (
    <div className="space-y-2">
      <span
        className={`inline-flex items-center rounded-sm border px-2.5 py-1 text-xs font-bold uppercase tracking-wide ${BAND_STYLES[band]}`}
      >
        Confidence: {band} ({pct}%)
      </span>
      {band === 'low' && (
        <p className="rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900" role="status">
          Low confidence — this answer may be incomplete. Prefer rephrasing your question
          or escalating to a human IP facilitator rather than relying on this alone.
        </p>
      )}
    </div>
  )
}
