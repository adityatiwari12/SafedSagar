import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { isRtl } from '../api/languages'
import { useLanguage } from '../i18n/LanguageContext'
import { EmptyState, StatusBadge } from '../ui/primitives'
import { useChatSession } from './useChatSession'
import { MessageBubble, ClarifyingQuestionBubble } from './MessageBubble'
import { ClarifyingQuestionForm } from './ClarifyingQuestionForm'
import { AnswerPanel } from './AnswerPanel'
import { JourneyStepper, deriveJourneyStep } from './JourneyStepper'
import { ThinkingIndicator } from './ThinkingIndicator'
import { ChatHistorySidebar } from './ChatHistorySidebar'
import { GuidedIntakeForm } from './GuidedIntakeForm'
import { AssessmentRail } from './AssessmentRail'
import { EscalateButton } from './EscalateButton'
import { useSpeechRecognition } from './useSpeechRecognition'

export default function ChatPage() {
  const session = useChatSession()
  const { t } = useLanguage()
  const [draft, setDraft] = useState('')
  const [showGuided, setShowGuided] = useState(false)
  const location = useLocation()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  // Snapshot of whatever was already typed when the mic was pressed, so
  // interim speech results replace only the dictated portion instead of
  // stacking duplicate partials onto themselves on every onresult event.
  const dictationBaseRef = useRef('')
  const speech = useSpeechRecognition(session.language, (text, isFinal) => {
    const base = dictationBaseRef.current
    setDraft(base ? `${base} ${text}` : text)
    if (isFinal) dictationBaseRef.current = base ? `${base} ${text}` : text
  })

  // Multi-round intake means a "final" answer and a mid-conversation
  // follow-up question both land here as ordinary turns - either way, once
  // the turn is back to idle the composer is exactly what the user should
  // type into next, so pull focus back to it instead of leaving it wherever
  // it landed (e.g. dropped by the textarea's own disabled-while-sending
  // state).
  useEffect(() => {
    if (session.status === 'idle') {
      textareaRef.current?.focus()
    }
  }, [session.status])

  const examples = useMemo(() => [t('ask.s1'), t('ask.s2'), t('ask.s3')], [t])

  useEffect(() => {
    const navState = location.state as
      | {
          seededDraft?: string
          prefill?: string
          activeProduct?: { id: string; name: string }
        }
      | null
    const draftText = navState?.seededDraft ?? navState?.prefill
    if (draftText) setDraft(draftText)
    if (navState?.activeProduct) session.setActiveProduct(navState.activeProduct)
    if (draftText || navState?.activeProduct) {
      window.history.replaceState({}, '')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const latestAssistant = useMemo(() => {
    for (let i = session.turns.length - 1; i >= 0; i -= 1) {
      const turn = session.turns[i]
      if (turn.role === 'assistant' && turn.response) return turn.response
    }
    return null
  }, [session.turns])

  const activeStep =
    session.liveStep ??
    deriveJourneyStep({
      hasUserMessage: session.turns.some((turn) => turn.role === 'user'),
      pendingClarifying: Boolean(session.pendingClarifying?.length),
      latest: latestAssistant,
    })

  const canSend =
    session.status !== 'sending' && Boolean(draft.trim()) && !session.pendingClarifying

  async function submitDraft() {
    if (!canSend) return
    const text = draft
    setDraft('')
    await session.sendMessage(text)
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void submitDraft()
  }

  function onComposerKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void submitDraft()
    }
  }

  const composerRows = Math.min(6, Math.max(1, draft.split('\n').length))

  const statusStrip = latestAssistant && (
    <div className="flex flex-wrap items-center gap-2 border border-surface-border bg-white px-3 py-2">
      <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {t('chat.statusStrip')}
      </span>
      <StatusBadge
        status={latestAssistant.confidence_band}
        label={`${t('chat.sectionConfidence')}: ${latestAssistant.confidence_band}`}
      />
      <StatusBadge
        status="medium"
        label={latestAssistant.classification.product_type.replace(/_/g, ' ')}
      />
      <StatusBadge
        status="open"
        label={
          latestAssistant.jurisdiction === 'india'
            ? t('jurisdiction.india')
            : t('jurisdiction.international')
        }
      />
      {latestAssistant.citations.length > 0 && (
        <StatusBadge
          status="resolved"
          label={`${latestAssistant.citations.length} ${t('chat.sourcesShort')}`}
        />
      )}
    </div>
  )

  const mobileExtras = (
    <div className="flex flex-col gap-3">
      <EscalateButton
        emphasized={Boolean(latestAssistant?.escalate_recommended)}
        disabled={session.status === 'sending'}
        onEscalate={session.escalate}
      />
      <details className="border border-surface-border bg-white">
        <summary className="cursor-pointer px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          {t('chat.history')}
        </summary>
        <div className="h-64 border-t border-surface-border p-3">
          <ChatHistorySidebar
            activeConversationId={session.conversationId}
            onSelect={(id) => void session.loadConversation(id)}
            onNewChat={session.startNewChat}
            onDeleted={() => session.startNewChat()}
            refreshKey={session.turns.length}
          />
        </div>
      </details>
      <details className="border border-surface-border bg-white">
        <summary className="cursor-pointer px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          {t('chat.assessmentTitle')}
        </summary>
        <div className="border-t border-surface-border p-3">
          <AssessmentRail
            latest={latestAssistant}
            sending={session.status === 'sending'}
            onEscalate={session.escalate}
          />
        </div>
      </details>
    </div>
  )

  return (
    <AppWorkspaceShell
      dense
      showJourneyControls
      jurisdiction={session.jurisdiction}
      onJurisdictionChange={(j) => {
        void session.setJurisdiction(j)
      }}
      language={session.language}
      onLanguageChange={session.setLanguage}
    >
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
        <JourneyStepper active={activeStep} />
        {statusStrip}

        <div className="grid min-h-0 flex-1 gap-4 overflow-hidden lg:grid-cols-[15rem_1fr_20rem]">
          <div className="hidden min-h-0 lg:block">
            <ChatHistorySidebar
              activeConversationId={session.conversationId}
              onSelect={(id) => void session.loadConversation(id)}
              onNewChat={session.startNewChat}
              onDeleted={() => session.startNewChat()}
              refreshKey={session.turns.length}
            />
          </div>

          <div className="min-h-0 overflow-hidden">
            <div
              className="flex h-full min-h-0 flex-col overflow-hidden border border-surface-border bg-white"
              dir={isRtl(session.language) ? 'rtl' : 'ltr'}
            >
              <div className="scroll-thin min-h-0 flex-1 space-y-5 overflow-y-auto p-4 sm:p-5" aria-live="polite">
                <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
                  <div className="lg:hidden">{mobileExtras}</div>

                  {session.turns.length === 0 && showGuided && (
                    <GuidedIntakeForm
                      onCancel={() => setShowGuided(false)}
                      onComplete={(text) => {
                        setShowGuided(false)
                        void session.sendMessage(text)
                      }}
                    />
                  )}

                  {session.turns.length === 0 && !showGuided && (
                    <EmptyState
                      title={t('chat.emptyTitle')}
                      description={t('chat.emptyBody')}
                      action={
                        <div className="w-full space-y-4">
                          <p className="text-sm text-ink-muted">
                            {t('chat.emptyGuidedLead')}{' '}
                            <button
                              type="button"
                              className="font-semibold text-saffron-deep underline"
                              onClick={() => setShowGuided(true)}
                            >
                              {t('chat.emptyGuidedCta')}
                            </button>
                            .
                          </p>
                          <div>
                            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                              {t('chat.examplesHeading')}
                            </p>
                            <ul className="mt-2 space-y-2">
                              {examples.map((ex) => (
                                <li key={ex}>
                                  <button
                                    type="button"
                                    className="w-full border border-surface-border bg-white px-3 py-2 text-left text-sm text-ink hover:border-saffron hover:bg-ivory"
                                    onClick={() => setDraft(ex)}
                                  >
                                    {ex}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          </div>
                          <Link
                            to="/classify"
                            className="inline-block text-sm font-semibold text-forest underline-offset-2 hover:underline"
                          >
                            {t('chat.classifyLink')}
                          </Link>
                        </div>
                      }
                    />
                  )}

                  {session.turns.map((turn) => {
                    const isClarifyingTurn =
                      turn.role === 'assistant' &&
                      !turn.response?.answer &&
                      Boolean(turn.response?.clarifying_questions?.length)
                    const speakText =
                      turn.role === 'assistant'
                        ? turn.response?.answer ||
                          turn.response?.clarifying_questions?.[0] ||
                          turn.text
                        : undefined
                    return (
                      <MessageBubble key={turn.id} role={turn.role} speakText={speakText}>
                        {turn.role === 'user' && <p>{turn.text}</p>}
                        {turn.role === 'assistant' && turn.response && isClarifyingTurn && (
                          <ClarifyingQuestionBubble question={turn.response.clarifying_questions![0]} />
                        )}
                        {turn.role === 'assistant' && turn.response && !isClarifyingTurn && (
                          <AnswerPanel response={turn.response} />
                        )}
                        {turn.role === 'assistant' && !turn.response && turn.text && <p>{turn.text}</p>}
                      </MessageBubble>
                    )
                  })}

                  {session.status === 'sending' && <ThinkingIndicator liveStep={session.liveStep} />}
                </div>
              </div>

              {session.pendingClarifying && (
                <div className="shrink-0 border-t border-surface-border p-4">
                  <div className="mx-auto w-full max-w-3xl">
                    <ClarifyingQuestionForm
                      questions={session.pendingClarifying}
                      disabled={session.status === 'sending'}
                      onSubmit={(answers) => {
                        void session.answerClarifying(answers)
                      }}
                    />
                  </div>
                </div>
              )}

              {session.error && (
                <div className="shrink-0 border-t border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
                  <div className="mx-auto w-full max-w-3xl">
                    <p>{session.error}</p>
                    <button
                      type="button"
                      className="gov-btn-secondary mt-2 !py-1"
                      onClick={() => void session.retryLast()}
                    >
                      {t('chat.retry')}
                    </button>
                  </div>
                </div>
              )}

              <div className="shrink-0 border-t border-surface-border bg-ivory/40 p-3 sm:p-4">
                {session.activeProduct && (
                  <div className="mx-auto mb-2 flex w-full max-w-3xl items-center justify-between gap-2 border border-saffron/50 bg-orange-50 px-3 py-1.5 text-xs text-ink">
                    <span>
                      {t('chat.assessing')}:{' '}
                      <span className="font-semibold">{session.activeProduct.name}</span>
                    </span>
                    <button
                      type="button"
                      className="font-semibold text-ink-muted underline hover:text-ink"
                      onClick={() => session.setActiveProduct(null)}
                      aria-label={`${t('chat.dismiss')} ${session.activeProduct.name}`}
                    >
                      {t('chat.dismiss')}
                    </button>
                  </div>
                )}
                <form onSubmit={onSubmit} className="mx-auto w-full max-w-3xl">
                  <div className="flex items-end gap-2 border border-surface-border bg-white py-1.5 pl-3 pr-1.5 focus-within:border-saffron">
                    <label htmlFor="question" className="sr-only">
                      {t('chat.yourQuestion')}
                    </label>
                    <textarea
                      id="question"
                      ref={textareaRef}
                      className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-sm leading-relaxed text-ink placeholder:text-ink-faint focus-visible:outline-none"
                      placeholder={t('chat.composerPlaceholder')}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={onComposerKeyDown}
                      disabled={session.status === 'sending' || Boolean(session.pendingClarifying)}
                      rows={composerRows}
                    />
                    {speech.supported && (
                      <button
                        type="button"
                        aria-label={speech.listening ? t('chat.micStop') : t('chat.micStart')}
                        title={speech.listening ? t('chat.micListening') : t('chat.micStart')}
                        disabled={session.status === 'sending' || Boolean(session.pendingClarifying)}
                        onClick={() => {
                          if (!speech.listening) dictationBaseRef.current = draft
                          speech.toggle()
                        }}
                        className={`flex h-9 w-9 shrink-0 items-center justify-center border transition-colors disabled:opacity-50 ${
                          speech.listening
                            ? 'animate-pulse border-red-400 bg-red-50 text-red-600'
                            : 'border-surface-border bg-white text-ink-faint hover:border-saffron hover:text-saffron-deep'
                        }`}
                      >
                        <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
                          <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
                          <path
                            d="M5 11a7 7 0 0 0 14 0M12 18v3"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                          />
                        </svg>
                      </button>
                    )}
                    <button
                      type="submit"
                      aria-label={t('chat.send')}
                      title={t('chat.send')}
                      disabled={!canSend}
                      className="flex h-9 w-9 shrink-0 items-center justify-center bg-saffron text-white transition-colors hover:bg-saffron-deep disabled:bg-surface-border disabled:text-ink-faint"
                    >
                      <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
                        <path
                          d="M12 19V5M12 5L6 11M12 5l6 6"
                          stroke="currentColor"
                          strokeWidth="2.25"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                  </div>
                  <p className="mt-1.5 px-1 text-xs text-ink-faint">
                    {speech.error ? t('chat.micError') : t('chat.composerHint')}
                  </p>
                </form>
              </div>
            </div>
          </div>

          <aside className="scroll-thin hidden min-h-0 overflow-y-auto lg:block">
            <AssessmentRail
              latest={latestAssistant}
              sending={session.status === 'sending'}
              onEscalate={session.escalate}
            />
          </aside>
        </div>
      </div>
    </AppWorkspaceShell>
  )
}
