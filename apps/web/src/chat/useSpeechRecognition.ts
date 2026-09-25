import { useCallback, useEffect, useRef, useState } from 'react'
import { LanguageCode, speechLangTag } from '../api/languages'

// Minimal shape of the Web Speech API's SpeechRecognition - not in
// TypeScript's lib.dom.d.ts (still non-standard/vendor-prefixed), so
// declared locally rather than pulling in a @types package for a handful
// of fields.
interface SpeechRecognitionResultLike {
  isFinal: boolean
  0: { transcript: string }
}
interface SpeechRecognitionEventLike {
  resultIndex: number
  results: ArrayLike<SpeechRecognitionResultLike>
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  start(): void
  stop(): void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

/**
 * Mic-to-text via the browser's native SpeechRecognition - no server round
 * trip, no Bhashini dependency (see CLAUDE.md's voice-interface scope
 * note). Interim results stream through onTranscript as the user speaks;
 * the caller decides what "final" means for its own UI (e.g. only commit
 * on stop()).
 */
export function useSpeechRecognition(
  language: LanguageCode,
  onTranscript: (text: string, isFinal: boolean) => void,
) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const onTranscriptRef = useRef(onTranscript)
  onTranscriptRef.current = onTranscript

  const supported = getSpeechRecognitionCtor() !== null

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return
    setError(null)
    const recognition = new Ctor()
    recognition.lang = speechLangTag(language)
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (event) => {
      let text = ''
      let isFinal = false
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        text += result[0].transcript
        if (result.isFinal) isFinal = true
      }
      onTranscriptRef.current(text, isFinal)
    }
    recognition.onerror = (event) => {
      // "no-speech"/"aborted" fire on ordinary silence or an explicit
      // stop() - not real errors, so don't surface them to the user.
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setError(event.error)
      }
    }
    recognition.onend = () => {
      setListening(false)
      recognitionRef.current = null
    }
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }, [language])

  useEffect(() => stop, [stop])

  const toggle = useCallback(() => {
    if (listening) stop()
    else start()
  }, [listening, start, stop])

  return { supported, listening, error, start, stop, toggle }
}
