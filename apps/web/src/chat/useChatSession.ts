import { useCallback, useRef, useState } from 'react'
import { chatApi, ChatTurnResponse, JourneyStepId } from '../api/chatApi'
import { conversationsApi } from '../api/conversationsApi'
import { ApiError } from '../api/http'
import { LanguageCode, isSupportedLanguage } from '../api/languages'

const LANGUAGE_STORAGE_KEY = 'ipsakti.language'

function loadStoredLanguage(): LanguageCode {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return (stored as LanguageCode) || 'en'
  } catch {
    return 'en' // localStorage can throw (private browsing, blocked storage) - fall back silently
  }
}

function storeLanguage(lang: LanguageCode) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang)
  } catch {
    // per-viewer convenience only - losing this is not worth surfacing an error for
  }
}

export interface Turn {
  id: string
  role: 'user' | 'assistant'
  text?: string
  response?: ChatTurnResponse
}

export interface ActiveProduct {
  id: string
  name: string
}

let turnCounter = 0
function nextTurnId() {
  turnCounter += 1
  return `turn-${turnCounter}`
}

export function useChatSession(initialProduct?: ActiveProduct | null) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [jurisdiction, setJurisdictionState] = useState<'india' | 'international'>('india')
  const [language, setLanguageState] = useState<LanguageCode>(loadStoredLanguage)
  // Product dossier the conversation is currently scoped to - included as
  // productId on every turn sent while set, so the Case that turn creates
  // links back to the product. Dismissing it (see clearActiveProduct)
  // clears it for turns going forward only; it never rewrites turns
  // already sent.
  const [activeProduct, setActiveProductState] = useState<ActiveProduct | null>(
    initialProduct ?? null,
  )
  const activeProductRef = useRef<ActiveProduct | null>(initialProduct ?? null)
  const [status, setStatus] = useState<'idle' | 'sending' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [pendingClarifying, setPendingClarifying] = useState<string[] | null>(null)
  // Real-time progress through the pipeline for the in-flight turn, driven
  // by /chat/ws step frames - null once idle (JourneyStepper falls back to
  // deriveJourneyStep for the last-finished/reopened state at that point).
  const [liveStep, setLiveStep] = useState<JourneyStepId | null>(null)
  // Mirrors conversationIdRef.current, purely so the history sidebar can
  // reactively highlight the active conversation - runTurn/loadConversation
  // read the ref directly (no re-render dependency needed there).
  const [conversationId, setConversationIdState] = useState<string | null>(null)
  const conversationIdRef = useRef<string | null>(null)
  const lastUserTextRef = useRef<string | null>(null)

  const setConversationId = useCallback((id: string | null) => {
    conversationIdRef.current = id
    setConversationIdState(id)
  }, [])

  const setActiveProduct = useCallback((product: ActiveProduct | null) => {
    activeProductRef.current = product
    setActiveProductState(product)
  }, [])

  const runTurn = useCallback(
    async (text: string, answers?: Record<string, string>, juris?: 'india' | 'international') => {
      setStatus('sending')
      setError(null)
      setLiveStep('language')
      try {
        const response = await chatApi.sendTurnStreaming(
          {
            conversationId: conversationIdRef.current,
            text,
            jurisdiction: juris ?? jurisdiction,
            answers,
            language,
            productId: activeProductRef.current?.id ?? null,
          },
          setLiveStep,
        )
        setConversationId(response.conversationId)

        if (response.clarifying_questions?.length) {
          setPendingClarifying(response.clarifying_questions)
          setTurns((prev) => [
            ...prev,
            {
              id: nextTurnId(),
              role: 'assistant',
              text: 'A few details will help classify your product accurately.',
              response,
            },
          ])
        } else {
          setPendingClarifying(null)
          setTurns((prev) => [
            ...prev,
            { id: nextTurnId(), role: 'assistant', response },
          ])
        }
        setStatus('idle')
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : 'Network error. Your question was kept — try again.'
        setError(message)
        setStatus('error')
      } finally {
        setLiveStep(null)
      }
    },
    [jurisdiction, language],
  )

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) return
      lastUserTextRef.current = trimmed
      setTurns((prev) => [...prev, { id: nextTurnId(), role: 'user', text: trimmed }])
      await runTurn(trimmed)
    },
    [runTurn],
  )

  const answerClarifying = useCallback(
    async (answers: Record<string, string>) => {
      const base = lastUserTextRef.current ?? ''
      const summary = Object.entries(answers)
        .map(([q, a]) => `${q}: ${a}`)
        .join('; ')
      const merged = `${base}\n\nClarifications: ${summary}`
      setTurns((prev) => [...prev, { id: nextTurnId(), role: 'user', text: summary }])
      setPendingClarifying(null)
      await runTurn(merged, answers)
    },
    [runTurn],
  )

  const setJurisdiction = useCallback(
    async (j: 'india' | 'international') => {
      setJurisdictionState(j)
      const last = lastUserTextRef.current
      if (!last) return
      setTurns((prev) => [
        ...prev,
        {
          id: nextTurnId(),
          role: 'user',
          text: `Switched jurisdiction to ${j === 'india' ? 'India' : 'International'} — re-analysing.`,
        },
      ])
      await runTurn(last, undefined, j)
    },
    [runTurn],
  )

  const setLanguage = useCallback((lang: LanguageCode) => {
    storeLanguage(lang)
    setLanguageState(lang)
  }, [])

  const escalate = useCallback(async () => {
    if (!conversationIdRef.current) return null
    return chatApi.escalate(conversationIdRef.current)
  }, [])

  const startNewChat = useCallback(() => {
    setConversationId(null)
    setTurns([])
    setPendingClarifying(null)
    setError(null)
    setStatus('idle')
    lastUserTextRef.current = null
  }, [setConversationId])

  const loadConversation = useCallback(
    async (id: string) => {
      setStatus('sending')
      setError(null)
      try {
        const messages = await conversationsApi.getMessages(id)
        const loadedTurns: Turn[] = messages.map((m) => ({
          id: nextTurnId(),
          role: m.role,
          // Kept for assistant turns too (not just user) - it's the fallback
          // render path when response_json is missing (rows from before that
          // column was populated), so the bubble isn't left blank.
          text: m.display_text,
          response: m.role === 'assistant' ? m.response ?? undefined : undefined,
        }))
        const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
        const lastUser = [...messages].reverse().find((m) => m.role === 'user')

        setConversationId(id)
        setTurns(loadedTurns)
        setPendingClarifying(lastAssistant?.response?.clarifying_questions?.length ? lastAssistant.response.clarifying_questions : null)
        lastUserTextRef.current = lastUser?.display_text ?? null
        if (isSupportedLanguage(lastUser?.language ?? lastAssistant?.language)) {
          setLanguage((lastUser?.language ?? lastAssistant?.language) as LanguageCode)
        }
        setStatus('idle')
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Could not load that conversation.'
        setError(message)
        setStatus('error')
      }
    },
    [setConversationId, setLanguage],
  )

  return {
    turns,
    conversationId,
    jurisdiction,
    language,
    status,
    error,
    pendingClarifying,
    liveStep,
    activeProduct,
    setActiveProduct,
    setLanguage,
    setJurisdiction,
    sendMessage,
    answerClarifying,
    escalate,
    startNewChat,
    loadConversation,
    retryLast: async () => {
      if (!lastUserTextRef.current) return
      await runTurn(lastUserTextRef.current)
    },
  }
}
