import { useEffect, useState } from 'react'
import type { JourneyStepId } from '../api/chatApi'
import { useLanguage } from '../i18n/LanguageContext'
import type { MessageKey } from '../i18n/types'

const STEP_TO_COPY: Partial<Record<JourneyStepId, MessageKey>> = {
  language: 'chat.stepLanguage',
  understand: 'chat.stepUnderstand',
  classify: 'chat.stepClassify',
  jurisdiction: 'chat.stepJurisdiction',
  need: 'chat.stepNeed',
  abs: 'chat.stepAbs',
  answer: 'chat.stepAnswer',
  action: 'chat.stepAction',
}

const FALLBACK_STAGES: MessageKey[] = [
  'chat.stepClassify',
  'chat.stepJurisdiction',
  'chat.stepNeed',
  'chat.stepAnswer',
  'chat.thinking',
]

const STAGE_INTERVAL_MS = 2800

/** Prefer live WebSocket step; otherwise advance a short curated sequence. */
export function ThinkingIndicator({ liveStep }: { liveStep?: JourneyStepId | null }) {
  const { t } = useLanguage()
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    if (liveStep) return
    setStageIndex(0)
    const id = window.setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, FALLBACK_STAGES.length - 1))
    }, STAGE_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [liveStep])

  const label = liveStep && STEP_TO_COPY[liveStep]
    ? t(STEP_TO_COPY[liveStep]!)
    : t(FALLBACK_STAGES[stageIndex] ?? 'chat.thinking')

  return (
    <p className="flex items-center gap-2 text-sm text-ink-muted" role="status" aria-live="polite">
      <span className="flex gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-saffron" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-saffron [animation-delay:0.2s]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-saffron [animation-delay:0.4s]" />
      </span>
      {label}
    </p>
  )
}
