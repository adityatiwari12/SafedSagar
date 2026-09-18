import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'
import { isRtl } from '../api/languages'
import { useLanguage } from '../i18n/LanguageContext'
import { useChatSession } from './useChatSession'
import { MessageBubble } from './MessageBubble'
import { ClarifyingQuestionForm } from './ClarifyingQuestionForm'
import { EscalateButton } from './EscalateButton'
import { AnswerPanel } from './AnswerPanel'
import { JourneyStepper, deriveJourneyStep } from './JourneyStepper'
import { ThinkingIndicator } from './ThinkingIndicator'
import { ChatHistorySidebar } from './ChatHistorySidebar'
import { GuidedIntakeForm } from './GuidedIntakeForm'

export default function ChatPage() {
  const session = useChatSession()
  const { t } = useLanguage()
  const [draft, setDraft] = useState('')
  const [showGuided, setShowGuided] = useState(false)
  const location = useLocation()

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

  const mobileExtras = (
    <div className="flex flex-col gap-3">
      <EscalateButton
        emphasized={Boolean(latestAssistant?.escalate_recommended)}
        disabled={session.status === 'sending'}
        onEscalate={session.escalate}
      />
      <details className="gov-panel">
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
      <details className="gov-panel">
        <summary className="cursor-pointer px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          {t('chat.howWorksDetails')}
        </summary>
        <div className="flex flex-col gap-3 border-t border-surface-border p-3">
          <GuidanceRail />
          <CorpusNote />
        </div>
      </details>
    </div>
  )

  return (
    <AppShell
      chatLayout
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

        <div className="grid min-h-0 flex-1 gap-4 overflow-hidden lg:grid-cols-[16rem_1fr_19rem]">
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
              className="gov-panel flex h-full min-h-0 flex-col overflow-hidden"
              dir={isRtl(session.language) ? 'rtl' : 'ltr'}
            >
              <div className="scroll-thin min-h-0 flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite">
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
                    <div className="rounded-sm border border-dashed border-surface-border bg-ivory p-5 text-sm text-ink-muted">
                      <p className="text-base font-semibold text-forest">{t('chat.emptyTitle')}</p>
                      <p className="mt-1">{t('chat.emptyBody')}</p>
                      <p className="mt-3">
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
                      <p className="mt-3 text-xs font-bold uppercase tracking-wide text-ink-faint">
                        {t('chat.examplesHeading')}
                      </p>
                      <ul className="mt-2 space-y-2">
                        {examples.map((ex) => (
                          <li key={ex}>
                            <button
                              type="button"
                              className="w-full rounded-sm border border-surface-border bg-white px-3 py-2 text-left text-sm text-ink hover:border-saffron hover:bg-ivory"
                              onClick={() => setDraft(ex)}
                            >
                              {ex}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {session.turns.map((turn) => (
                    <MessageBubble key={turn.id} role={turn.role}>
                      {turn.role === 'user' && <p>{turn.text}</p>}
                      {turn.role === 'assistant' && turn.response && (
                        <AnswerPanel response={turn.response} />
                      )}
                      {turn.role === 'assistant' && !turn.response && turn.text && <p>{turn.text}</p>}
                    </MessageBubble>
                  ))}

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

              <div className="shrink-0 border-t border-surface-border bg-white p-3 sm:p-4">
                {session.activeProduct && (
                  <div className="mx-auto mb-2 flex w-full max-w-3xl items-center justify-between gap-2 rounded-sm border border-saffron/50 bg-orange-50 px-3 py-1.5 text-xs text-ink">
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
                  <div className="flex items-end gap-2 rounded-sm border border-surface-border bg-white py-1.5 pl-3 pr-1.5 shadow-panel focus-within:border-saffron">
                    <label htmlFor="question" className="sr-only">
                      {t('chat.yourQuestion')}
                    </label>
                    <textarea
                      id="question"
                      className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-sm leading-relaxed text-ink placeholder:text-ink-faint focus-visible:outline-none"
                      placeholder={t('chat.composerPlaceholder')}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={onComposerKeyDown}
                      disabled={session.status === 'sending' || Boolean(session.pendingClarifying)}
                      rows={composerRows}
                    />
                    <button
                      type="submit"
                      aria-label={t('chat.send')}
                      title={t('chat.send')}
                      disabled={!canSend}
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm bg-saffron text-white transition-colors hover:bg-saffron-deep disabled:bg-surface-border disabled:text-ink-faint"
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
                  <p className="mt-1.5 px-2 text-xs text-ink-faint">{t('chat.composerHint')}</p>
                </form>
              </div>
            </div>
          </div>

          <aside className="scroll-thin hidden min-h-0 overflow-y-auto lg:block">
            <div className="flex flex-col gap-4 pb-1">
              <GuidanceRail />
              <EscalateButton
                emphasized={Boolean(latestAssistant?.escalate_recommended)}
                disabled={session.status === 'sending'}
                onEscalate={session.escalate}
              />
              <CorpusNote />
            </div>
          </aside>
        </div>
      </div>
    </AppShell>
  )
}

function GuidanceRail() {
  const { t } = useLanguage()
  return (
    <section className="gov-panel p-4 text-sm">
      <h2 className="font-bold text-forest">{t('chat.howWorksTitle')}</h2>
      <ol className="mt-2 list-decimal space-y-1 pl-4 text-ink-muted">
        <li>{t('chat.how1')}</li>
        <li>{t('chat.how2')}</li>
        <li>{t('chat.how3')}</li>
        <li>{t('chat.how4')}</li>
        <li>{t('chat.how5')}</li>
      </ol>
      <Link to="/classify" className="mt-3 inline-block text-sm font-semibold text-saffron-deep underline">
        {t('chat.classifyLink')}
      </Link>
    </section>
  )
}

function CorpusNote() {
  const { t } = useLanguage()
  return (
    <section className="gov-panel p-4 text-xs text-ink-muted">
      <p className="font-semibold text-ink">{t('chat.corpusTitle')}</p>
      <p className="mt-1">{t('chat.corpusBody')}</p>
    </section>
  )
}
