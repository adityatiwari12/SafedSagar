import { ReactNode } from 'react'
import { useLanguage } from '../i18n/LanguageContext'

export function MessageBubble({
  role,
  children,
}: {
  role: 'user' | 'assistant'
  children: ReactNode
}) {
  const { t } = useLanguage()
  const isUser = role === 'user'

  if (isUser) {
    return (
      <div className="border-l-2 border-saffron bg-ivory/80 px-4 py-3">
        <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
          {t('chat.queryLabel')}
        </p>
        <div className="text-sm leading-relaxed text-ink">{children}</div>
      </div>
    )
  }

  return (
    <div>
      <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {t('chat.assessmentLabel')}
      </p>
      {children}
    </div>
  )
}

/**
 * A mid-conversation follow-up question from the multi-round intake
 * (backend: assess_intake / reason_and_cite, capped at 5 rounds by
 * chat/router.py's _INTAKE_ROUND_CAP). Deliberately light - conversational
 * text plus a small quiet marker, not the full AnswerPanel treatment, since
 * there's no classification/citations/confidence to show yet and this is
 * now the normal shape of an in-progress exchange, not a rare case.
 */
export function ClarifyingQuestionBubble({ question }: { question: string }) {
  const { t } = useLanguage()
  return (
    <div>
      <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-faint">
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M9.5 9.3a2.5 2.5 0 1 1 3.7 2.2c-.9.5-1.2 1-1.2 2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="12" cy="17" r="0.9" fill="currentColor" />
        </svg>
        {t('chat.followUpLabel')}
      </p>
      <p className="max-w-[70ch] text-sm leading-relaxed text-ink">{question}</p>
    </div>
  )
}
