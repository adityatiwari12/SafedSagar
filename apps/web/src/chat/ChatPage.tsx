import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'
import { isRtl } from '../api/languages'
import { useChatSession } from './useChatSession'
import { MessageBubble } from './MessageBubble'
import { ClarifyingQuestionForm } from './ClarifyingQuestionForm'
import { EscalateButton } from './EscalateButton'
import { AnswerPanel } from './AnswerPanel'
import { JourneyStepper, deriveJourneyStep } from './JourneyStepper'
import { ThinkingIndicator } from './ThinkingIndicator'
import { ChatHistorySidebar } from './ChatHistorySidebar'
import { GuidedIntakeForm } from './GuidedIntakeForm'

const EXAMPLES = [
  'I developed a new Ayurvedic formulation using Ashwagandha. Can I patent it?',
  'What ABS obligations apply if I commercially use Indian medicinal plants?',
  'We want to market an Ayurveda Aahara food product — what FSSAI rules apply?',
]

export default function ChatPage() {
  const session = useChatSession()
  const [draft, setDraft] = useState('')
  const [showGuided, setShowGuided] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const seeded = (location.state as { seededDraft?: string } | null)?.seededDraft
    if (seeded) {
      setDraft(seeded)
      // Clear so a page refresh / back-nav doesn't re-seed the draft.
      window.history.replaceState({}, '')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const latestAssistant = useMemo(() => {
    for (let i = session.turns.length - 1; i >= 0; i -= 1) {
      const t = session.turns[i]
      if (t.role === 'assistant' && t.response) return t.response
    }
    return null
  }, [session.turns])

  // Live /chat/ws progress while a turn is in flight; once it settles,
  // fall back to deriving from the last finished response (also covers
  // conversations reopened from history, which have no live events).
  const activeStep =
    session.liveStep ??
    deriveJourneyStep({
      hasUserMessage: session.turns.some((t) => t.role === 'user'),
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
    // Enter sends, Shift+Enter inserts a newline - standard chat-composer
    // convention (ChatGPT, Slack, etc).
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void submitDraft()
    }
  }

  const composerRows = Math.min(6, Math.max(1, draft.split('\n').length))

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
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <JourneyStepper active={activeStep} />

        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[16rem_1fr_19rem]">
          <div className="hidden min-h-0 lg:block">
            <ChatHistorySidebar
              activeConversationId={session.conversationId}
              onSelect={(id) => void session.loadConversation(id)}
              onNewChat={session.startNewChat}
              onDeleted={() => session.startNewChat()}
              refreshKey={session.turns.length}
            />
          </div>

          <div className="min-h-0">
            {/* dir scoped to just the chat panel - task Section 8: don't make
                the whole app RTL when Urdu isn't active. */}
            <div
              className="gov-panel flex h-full min-h-0 flex-col overflow-hidden"
              dir={isRtl(session.language) ? 'rtl' : 'ltr'}
            >
              <div className="scroll-thin min-h-0 flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite">
                <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
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
                    <div className="rounded-lg border border-dashed border-surface-border bg-surface-muted/60 p-5 text-sm text-ink-muted">
                      <p className="text-base font-semibold text-navy">
                        Describe your product or IP question
                      </p>
                      <p className="mt-1">
                        Ministry of Ayush guidance for Ayurveda practitioners, researchers,
                        startups and cultivators. India and international jurisdictions are kept
                        separate — set the toggle above before or during your conversation.
                      </p>
                      <p className="mt-3">
                        Try one of these, write your own below, or{' '}
                        <button
                          type="button"
                          className="font-semibold text-primary underline"
                          onClick={() => setShowGuided(true)}
                        >
                          let us walk you through it step by step
                        </button>
                        .
                      </p>
                      <ul className="mt-3 space-y-2">
                        {EXAMPLES.map((ex) => (
                          <li key={ex}>
                            <button
                              type="button"
                              className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-left text-sm text-ink hover:border-primary hover:bg-blue-50"
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

                  {session.status === 'sending' && <ThinkingIndicator />}
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
                      Retry
                    </button>
                  </div>
                </div>
              )}

              <div className="shrink-0 border-t border-surface-border bg-white p-3 sm:p-4">
                <form onSubmit={onSubmit} className="mx-auto w-full max-w-3xl">
                  <div className="flex items-end gap-2 rounded-3xl border border-surface-border bg-white py-1.5 pl-4 pr-1.5 shadow-panel focus-within:border-saffron">
                    <label htmlFor="question" className="sr-only">
                      Your question
                    </label>
                    <textarea
                      id="question"
                      className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-sm leading-relaxed text-ink outline-none placeholder:text-ink-faint"
                      placeholder="Describe your product or ask an IP / ABS / regulatory question…"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={onComposerKeyDown}
                      disabled={session.status === 'sending' || Boolean(session.pendingClarifying)}
                      rows={composerRows}
                    />
                    <button
                      type="submit"
                      aria-label="Send message"
                      title="Send (Enter)"
                      disabled={!canSend}
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-saffron text-white transition-colors hover:bg-saffron-deep disabled:bg-surface-border disabled:text-ink-faint"
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
                  <p className="mt-1.5 px-2 text-xs text-ink-faint">
                    Enter to send, Shift+Enter for a new line. Not official Ayush advice — confirm
                    filings against source gazettes.
                  </p>
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

        {/* Below lg there's no room for three independently-scrolling
            columns, so history and guidance collapse into compact
            <details> rows above the conversation instead of a 3-column
            grid - escalation stays a direct action, not tucked away. */}
        <div className="flex flex-col gap-3 lg:hidden">
          <EscalateButton
            emphasized={Boolean(latestAssistant?.escalate_recommended)}
            disabled={session.status === 'sending'}
            onEscalate={session.escalate}
          />

          <details className="gov-panel">
            <summary className="cursor-pointer px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
              Chat history
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
              How this works &amp; corpus note
            </summary>
            <div className="flex flex-col gap-3 border-t border-surface-border p-3">
              <GuidanceRail />
              <CorpusNote />
            </div>
          </details>
        </div>
      </div>
    </AppShell>
  )
}

function GuidanceRail() {
  return (
    <section className="gov-panel p-4 text-sm">
      <h2 className="font-bold text-navy">How this works</h2>
      <ol className="mt-2 list-decimal space-y-1 pl-4 text-ink-muted">
        <li>Choose language &amp; jurisdiction</li>
        <li>Describe the product</li>
        <li>Answer any clarifying questions</li>
        <li>Review classification, citations &amp; action plan</li>
        <li>Escalate if confidence is low</li>
      </ol>
      <Link to="/classify" className="mt-3 inline-block text-sm font-semibold text-primary underline">
        Not sure what category your product is? Use the classification wizard →
      </Link>
    </section>
  )
}

function CorpusNote() {
  return (
    <section className="gov-panel p-4 text-xs text-ink-muted">
      <p className="font-semibold text-ink">Corpus note</p>
      <p className="mt-1">
        Answers cite Wave A statutes, rules, treaties and selected case law. TKDL is
        awareness-only (not retrieved). GRATK is signed, not yet in force.
      </p>
    </section>
  )
}
