import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { useTextToSpeech } from './useTextToSpeech'

let speakMock: ReturnType<typeof vi.fn>
let cancelMock: ReturnType<typeof vi.fn>
let lastUtterance: SpeechSynthesisUtterance | null

beforeEach(() => {
  speakMock = vi.fn((utterance: SpeechSynthesisUtterance) => {
    lastUtterance = utterance
  })
  cancelMock = vi.fn()
  lastUtterance = null
  vi.stubGlobal('speechSynthesis', { speak: speakMock, cancel: cancelMock, speaking: false })
  vi.stubGlobal(
    'SpeechSynthesisUtterance',
    vi.fn().mockImplementation((text: string) => ({ text, lang: '' })),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('supported is true when speechSynthesis exists on window', () => {
  const { result } = renderHook(() => useTextToSpeech())
  expect(result.current.supported).toBe(true)
})

test('speak() cancels any prior utterance, then speaks the new one tagged with the language', () => {
  const { result } = renderHook(() => useTextToSpeech())

  act(() => {
    result.current.speak('Tablets made from ashwagandha extract are...', 'hi')
  })

  expect(cancelMock).toHaveBeenCalledTimes(1)
  expect(speakMock).toHaveBeenCalledTimes(1)
  expect(lastUtterance?.lang).toBe('hi-IN')
})

test('speak() with empty/whitespace text is a no-op', () => {
  const { result } = renderHook(() => useTextToSpeech())

  act(() => {
    result.current.speak('   ', 'en')
  })

  expect(speakMock).not.toHaveBeenCalled()
})

test('cancel() stops speech synthesis and clears the speaking flag', () => {
  const { result } = renderHook(() => useTextToSpeech())

  act(() => {
    result.current.cancel()
  })

  expect(cancelMock).toHaveBeenCalledTimes(1)
  expect(result.current.speaking).toBe(false)
})

test('supported is false when speechSynthesis is unavailable', () => {
  vi.unstubAllGlobals()
  const { result } = renderHook(() => useTextToSpeech())
  expect(result.current.supported).toBe(false)
})
