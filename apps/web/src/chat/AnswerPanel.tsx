import { ChatTurnResponse } from '../api/chatApi'
import { CitationList } from './CitationList'
import { ClassificationBadges } from './ClassificationBadges'
import { ConfidenceBadge } from './ConfidenceBadge'

export function AnswerPanel({ response }: { response: ChatTurnResponse }) {
  if (!response.answer && response.clarifying_questions?.length) return null

  return (
    <div className="space-y-4">
      {(response.classification.product_type !== 'unknown' ||
        response.classification.ip_type !== 'unknown') && (
        <ClassificationBadges
          productType={response.classification.product_type}
          ipType={response.classification.ip_type}
          jurisdiction={response.jurisdiction}
        />
      )}

      <ConfidenceBadge band={response.confidence_band} confidence={response.confidence} />

      {response.answer && (
        <div className="prose-sm whitespace-pre-wrap text-ink">{response.answer}</div>
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

      <CitationList citations={response.citations} />

      {response.next_steps && response.next_steps.length > 0 && (
        <section className="gov-panel border-l-4 border-indiaGreen p-4" aria-labelledby="next-steps">
          <h3 id="next-steps" className="text-base font-bold text-navy">
            Action plan — what to do next
          </h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-ink">
            {response.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}
