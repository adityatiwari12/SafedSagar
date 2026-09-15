import { FormEvent, useEffect, useMemo, useState } from 'react'
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

  const activeStep = deriveJourneyStep({
    hasUserMessage: session.turns.some((t) => t.role === 'user'),
    pendingClarifying: Boolean(session.pendingClarifying?.length),
    latest: latestAssistant,
  })

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const text = draft
    setDraft('')
    await session.sendMessage(text)
  }

  return (
    <AppShell
      showJourneyControls
      jurisdiction={session.jurisdiction}
      onJurisdictionChange={(j) => {
        void session.setJurisdiction(j)
      }}
      language={session.language}
      onLanguageChange={session.setLanguage}
    >
      <div className="space-y-5">
        <header className="space-y-2">
          <h1 className="text-2xl font-bold text-navy sm:text-3xl">IP-SAKTI Sahayak</h1>
          <p className="max-w-3xl text-sm text-ink-muted sm:text-base">
            Ministry of Ayush service for Ayurveda practitioners, researchers, startups and
            cultivators. Describe your product or IP question. India and international
            jurisdictions are kept separate — set the toggle before or during your conversation.
          </p>
        </header>

        <JourneyStepper active={activeStep} />

        <div className="grid gap-5 lg:grid-cols-[14rem_1fr_18rem]">
          <ChatHistorySidebar
            activeConversationId={session.conversationId}
            onSelect={(id) => void session.loadConversation(id)}
            onNewChat={session.startNewChat}
            refreshKey={session.turns.length}
          />

          <div className="space-y-4">
            {/* dir scoped to just the chat panel - task Section 8: don't make
                the whole app RTL when Urdu isn't active. */}
            <div
              className="gov-panel flex min-h-[22rem] flex-col"
              dir={isRtl(session.language) ? 'rtl' : 'ltr'}
            >
              <div className="border-b border-surface-border bg-surface-muted px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                Conversation
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
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
                  <div className="rounded-sm border border-dashed border-surface-border bg-surface-muted/60 p-4 text-sm text-ink-muted">
                    <p className="font-semibold text-navy">Start with a clear product description</p>
                    <p className="mt-1">
                      Try one of these examples, write your own question below, or{' '}
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
                            className="w-full rounded-sm border border-surface-border bg-white px-3 py-2 text-left text-sm text-ink hover:border-primary hover:bg-blue-50"
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

              {session.pendingClarifying && (
                <div className="border-t border-surface-border p-4">
                  <ClarifyingQuestionForm
                    questions={session.pendingClarifying}
                    disabled={session.status === 'sending'}
                    onSubmit={(answers) => {
                      void session.answerClarifying(answers)
                    }}
                  />
                </div>
              )}

              {session.error && (
                <div className="border-t border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
                  <p>{session.error}</p>
                  <button
                    type="button"
                    className="gov-btn-secondary mt-2 !py-1"
                    onClick={() => void session.retryLast()}
                  >
                    Retry
                  </button>
                </div>
              )}

              <form
                onSubmit={onSubmit}
                className="flex flex-col gap-2 border-t border-surface-border p-4 sm:flex-row"
              >
                <label htmlFor="question" className="sr-only">
                  Your question
                </label>
                <textarea
                  id="question"
                  className="gov-input min-h-[3rem] flex-1 resize-y"
                  placeholder="Describe your product or ask an IP / ABS / regulatory question…"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={session.status === 'sending' || Boolean(session.pendingClarifying)}
                  rows={2}
                />
                <button
                  type="submit"
                  className="gov-btn-primary self-stretch sm:self-end"
                  disabled={
                    session.status === 'sending' ||
                    !draft.trim() ||
                    Boolean(session.pendingClarifying)
                  }
                >
                  Ask Sahayak
                </button>
              </form>
            </div>
          </div>

          <aside className="space-y-4">
            <section className="gov-panel p-4 text-sm">
              <h2 className="font-bold text-navy">How this works</h2>
              <ol className="mt-2 list-decimal space-y-1 pl-4 text-ink-muted">
                <li>Choose language &amp; jurisdiction</li>
                <li>Describe the product</li>
                <li>Answer any clarifying questions</li>
                <li>Review classification, citations &amp; action plan</li>
                <li>Escalate if confidence is low</li>
              </ol>
              <Link
                to="/classify"
                className="mt-3 inline-block text-sm font-semibold text-primary underline"
              >
                Not sure what category your product is? Use the classification wizard →
              </Link>
            </section>

            <EscalateButton
              emphasized={Boolean(latestAssistant?.escalate_recommended)}
              disabled={session.status === 'sending'}
              onEscalate={session.escalate}
            />

            <section className="gov-panel p-4 text-xs text-ink-muted">
              <p className="font-semibold text-ink">Corpus note</p>
              <p className="mt-1">
                Answers cite Wave A statutes, rules, treaties and selected case law. TKDL is
                awareness-only (not retrieved). GRATK is signed, not yet in force.
              </p>
            </section>
          </aside>
        </div>
      </div>
    </AppShell>
  )
}
