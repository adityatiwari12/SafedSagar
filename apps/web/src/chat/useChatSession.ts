import { useCallback, useRef, useState } from 'react'
import { chatApi, ChatTurnResponse } from '../api/chatApi'
import { ApiError } from '../api/http'

export interface Turn {
  id: string
  role: 'user' | 'assistant'
  text?: string
  response?: ChatTurnResponse
}

let turnCounter = 0
function nextTurnId() {
  turnCounter += 1
  return `turn-${turnCounter}`
}

export function useChatSession() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [jurisdiction, setJurisdictionState] = useState<'india' | 'international'>('india')
  const [language, setLanguage] = useState<'en' | 'hi'>('en')
  const [status, setStatus] = useState<'idle' | 'sending' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [pendingClarifying, setPendingClarifying] = useState<string[] | null>(null)
  const conversationIdRef = useRef<string | null>(null)
  const lastUserTextRef = useRef<string | null>(null)

  const runTurn = useCallback(
    async (text: string, answers?: Record<string, string>, juris?: 'india' | 'international') => {
      setStatus('sending')
      setError(null)
      try {
        const response = await chatApi.sendTurn({
          conversationId: conversationIdRef.current,
          text,
          jurisdiction: juris ?? jurisdiction,
          answers,
          language,
        })
        conversationIdRef.current = response.conversationId

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

  const escalate = useCallback(async () => {
    if (!conversationIdRef.current) return null
    return chatApi.escalate(conversationIdRef.current)
  }, [])

  return {
    turns,
    jurisdiction,
    language,
    status,
    error,
    pendingClarifying,
    setLanguage,
    setJurisdiction,
    sendMessage,
    answerClarifying,
    escalate,
    retryLast: async () => {
      if (!lastUserTextRef.current) return
      await runTurn(lastUserTextRef.current)
    },
  }
}
