import { useState } from 'react'
import { ChatTurnResponse } from '../api/chatApi'
import { CitationList } from './CitationList'

const BAND_DOT = {
  high: 'bg-ayush-bright',
  medium: 'bg-saffron',
  low: 'bg-red-600',
} as const

export function AnswerPanel({ response }: { response: ChatTurnResponse }) {
  const [showEnglish, setShowEnglish] = useState(false)

  if (!response.answer && response.clarifying_questions?.length) return null

  const hasClassification =
    response.classification.product_type !== 'unknown' || response.classification.ip_type !== 'unknown'
  const pct = Math.round(response.confidence * 100)

  const isTranslated = Boolean(
    response.detected_language && response.detected_language !== 'en' && response.canonical_answer,
  )

  return (
    <div className="space-y-3">
      {/* The answer reads first, as chat text - not buried under badges. */}
      {response.answer && (
        <div
          className="whitespace-pre-wrap text-[0.95rem] leading-relaxed text-ink"
          lang={showEnglish ? 'en' : response.detected_language || 'en'}
        >
          {showEnglish && response.canonical_answer ? response.canonical_answer : response.answer}
        </div>
      )}

      {/* One compact meta line instead of stacked badges - classification,
          confidence, and translation status are useful context, not the
          headline of every reply. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-faint">
        {hasClassification && (
          <span className="capitalize">
            {response.classification.product_type.replace(/_/g, ' ')} ·{' '}
            {response.jurisdiction === 'india' ? 'India' : 'International'}
          </span>
        )}
        <span className="inline-flex items-center gap-1">
          <span className={`h-1.5 w-1.5 rounded-full ${BAND_DOT[response.confidence_band]}`} aria-hidden="true" />
          Confidence: {response.confidence_band} ({pct}%)
        </span>
        {isTranslated && (
          <button
            type="button"
            className="underline decoration-dotted hover:text-ink-muted"
            onClick={() => setShowEnglish((v) => !v)}
          >
            {showEnglish ? 'View translated' : 'View in English'}
          </button>
        )}
        {response.needs_human_review && (
          <span className="text-amber-800">Translation unverified - showing safest available text</span>
        )}
      </div>

      {response.confidence_band === 'low' && (
        <p className="rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900" role="status">
          Low confidence — this answer may be incomplete. Prefer rephrasing your question or
          escalating to a human IP facilitator rather than relying on this alone.
        </p>
      )}

      {response.abs_tk_flags &&
        (response.abs_tk_flags.biological_resource_likely ||
          response.abs_tk_flags.traditional_knowledge_likely) && (
          <aside
            className="rounded-sm border border-saffron/60 bg-orange-50 p-3 text-sm text-ink"
            aria-label="ABS and traditional knowledge check"
          >
            <p className="font-bold text-navy">ABS / TK check</p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {response.abs_tk_flags.biological_resource_likely && (
                <li>Biological resource indicators present — ABS approval may be required.</li>
              )}
              {response.abs_tk_flags.traditional_knowledge_likely && (
                <li>
                  Traditional knowledge indicators present — TKDL prior art may exist (contact
                  CSIR-TKDL; contents are not retrieved here).
                </li>
              )}
            </ul>
            {response.abs_tk_flags.note && (
              <p className="mt-2 text-ink-muted">{response.abs_tk_flags.note}</p>
            )}
          </aside>
        )}

      {response.citations.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer font-semibold text-primary hover:text-primary-dark">
            Sources ({response.citations.length})
          </summary>
          <CitationList citations={response.citations} />
        </details>
      )}

      {response.next_steps && response.next_steps.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer font-semibold text-primary hover:text-primary-dark">
            Suggested next steps
          </summary>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-ink">
            {response.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </details>
      )}
    </div>
  )
}
