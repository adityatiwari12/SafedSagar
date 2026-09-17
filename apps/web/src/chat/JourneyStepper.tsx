import { ChatTurnResponse, JourneyStepId } from '../api/chatApi'

export type { JourneyStepId }

// Order matches chat/router.py's NODE_TO_STEP / the graph's real node
// execution order (condense_query -> classify_product -> route_jurisdiction
// -> route_ip_type/retrieve/rerank -> reason_and_cite/validate_citations ->
// score_confidence/escalate_if_needed), not an arbitrary UI-authored guess -
// a live /chat/ws turn lights these up in exactly this left-to-right order.
const STEPS: { id: JourneyStepId; label: string }[] = [
  { id: 'language', label: 'Language' },
  { id: 'understand', label: 'Understand' },
  { id: 'classify', label: 'Classify' },
  { id: 'jurisdiction', label: 'Jurisdiction' },
  { id: 'need', label: 'Identify need' },
  { id: 'abs', label: 'ABS / TK' },
  { id: 'answer', label: 'Answer' },
  { id: 'action', label: 'Action plan' },
]

export function deriveJourneyStep(opts: {
  hasUserMessage: boolean
  pendingClarifying: boolean
  latest?: ChatTurnResponse | null
}): JourneyStepId {
  const { hasUserMessage, pendingClarifying, latest } = opts
  // Fallback for turns with no live step events to replay (reopening a
  // past conversation from history, or a turn sent before this session
  // saw any WebSocket frames) - best-effort guess from the finished
  // response alone, same as before live streaming existed.
  if (!hasUserMessage) return 'language'
  if (pendingClarifying) return 'understand'
  if (!latest || !latest.answer) return 'understand'
  if (latest.classification.product_type === 'unknown') return 'classify'
  if (latest.classification.product_type === 'out_of_scope') return 'classify'
  if (latest.abs_tk_flags && (latest.abs_tk_flags.biological_resource_likely || latest.abs_tk_flags.traditional_knowledge_likely)) {
    if (!latest.next_steps?.length) return 'abs'
  }
  if (latest.next_steps?.length) return 'action'
  return 'answer'
}

export function JourneyStepper({ active }: { active: JourneyStepId }) {
  const activeIndex = STEPS.findIndex((s) => s.id === active)

  return (
    <nav aria-label="Guidance journey" className="gov-panel overflow-x-auto p-3">
      <ol className="flex min-w-max gap-1">
        {STEPS.map((step, i) => {
          const done = i < activeIndex
          const current = i === activeIndex
          return (
            <li key={step.id} className="flex items-center gap-1">
              <div
                className={`flex items-center gap-2 rounded-sm px-2.5 py-1.5 text-xs font-semibold ${
                  current
                    ? 'bg-primary text-white'
                    : done
                      ? 'bg-indiaGreen/15 text-indiaGreen'
                      : 'bg-surface-muted text-ink-faint'
                }`}
                aria-current={current ? 'step' : undefined}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                    current ? 'bg-white text-primary' : done ? 'bg-indiaGreen text-white' : 'bg-white text-ink-faint'
                  }`}
                >
                  {i + 1}
                </span>
                {step.label}
              </div>
              {i < STEPS.length - 1 && (
                <span className="px-0.5 text-ink-faint" aria-hidden="true">
                  ›
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
