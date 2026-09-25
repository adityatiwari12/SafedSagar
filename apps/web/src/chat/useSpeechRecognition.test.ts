import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { useSpeechRecognition } from './useSpeechRecognition'

class FakeSpeechRecognition {
  lang = ''
  continuous = false
  interimResults = false
  onresult: ((event: unknown) => void) | null = null
  onerror: ((event: { error: string }) => void) | null = null
  onend: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn(() => {
    this.onend?.()
  })
}

let lastInstance: FakeSpeechRecognition | null = null

beforeEach(() => {
  lastInstance = null
  vi.stubGlobal(
    'SpeechRecognition',
    vi.fn().mockImplementation(() => {
      lastInstance = new FakeSpeechRecognition()
      return lastInstance
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('supported is true when SpeechRecognition exists on window', () => {
  const { result } = renderHook(() => useSpeechRecognition('en', vi.fn()))
  expect(result.current.supported).toBe(true)
})

test('start() creates a recognizer tagged with the BCP-47 language and begins listening', () => {
  const { result } = renderHook(() => useSpeechRecognition('hi', vi.fn()))

  act(() => {
    result.current.start()
  })

  expect(lastInstance?.lang).toBe('hi-IN')
  expect(lastInstance?.start).toHaveBeenCalledTimes(1)
  expect(result.current.listening).toBe(true)
})

test('a result event forwards the transcript and final flag to onTranscript', () => {
  const onTranscript = vi.fn()
  const { result } = renderHook(() => useSpeechRecognition('en', onTranscript))

  act(() => {
    result.current.start()
  })
  act(() => {
    lastInstance?.onresult?.({
      resultIndex: 0,
      results: [{ isFinal: true, 0: { transcript: 'ashwagandha patent question' } }],
    })
  })

  expect(onTranscript).toHaveBeenCalledWith('ashwagandha patent question', true)
})

test('stop() ends listening', () => {
  const { result } = renderHook(() => useSpeechRecognition('en', vi.fn()))

  act(() => {
    result.current.start()
  })
  act(() => {
    result.current.stop()
  })

  expect(result.current.listening).toBe(false)
})

test('a "no-speech" error is swallowed, not surfaced', () => {
  const { result } = renderHook(() => useSpeechRecognition('en', vi.fn()))

  act(() => {
    result.current.start()
  })
  act(() => {
    lastInstance?.onerror?.({ error: 'no-speech' })
  })

  expect(result.current.error).toBeNull()
})

test('any other error is surfaced', () => {
  const { result } = renderHook(() => useSpeechRecognition('en', vi.fn()))

  act(() => {
    result.current.start()
  })
  act(() => {
    lastInstance?.onerror?.({ error: 'network' })
  })

  expect(result.current.error).toBe('network')
})

test('supported is false when SpeechRecognition is unavailable', () => {
  vi.unstubAllGlobals()
  const { result } = renderHook(() => useSpeechRecognition('en', vi.fn()))
  expect(result.current.supported).toBe(false)
})
