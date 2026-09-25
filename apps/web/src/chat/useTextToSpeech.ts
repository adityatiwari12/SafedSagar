import { useCallback, useEffect, useState } from 'react'
import { LanguageCode, speechLangTag } from '../api/languages'

/**
 * Reads text aloud via the browser's native speechSynthesis - no server
 * round trip, no Bhashini dependency (see CLAUDE.md's voice-interface
 * scope note). Voice availability per language is entirely up to the
 * browser/OS; speaking still proceeds without a language-matched voice
 * (falls back to the engine's default), it just may not sound native.
 */
export function useTextToSpeech() {
  const [speaking, setSpeaking] = useState(false)
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window

  useEffect(() => {
    if (!supported) return
    // Catches speech stopped by any means, not just our own cancel() calls
    // (e.g. the browser tab losing focus on some platforms).
    const interval = window.setInterval(() => {
      setSpeaking(window.speechSynthesis.speaking)
    }, 300)
    return () => window.clearInterval(interval)
  }, [supported])

  const cancel = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [supported])

  const speak = useCallback(
    (text: string, language: LanguageCode) => {
      if (!supported || !text.trim()) return
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = speechLangTag(language)
      utterance.onstart = () => setSpeaking(true)
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(utterance)
    },
    [supported],
  )

  return { supported, speaking, speak, cancel }
}
