import { fireEvent, render, screen } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { SpeakButton } from './SpeakButton'
import { LanguageProvider } from '../i18n/LanguageContext'

function wrapper(props: { children: ReactNode }) {
  return createElement(LanguageProvider, null, props.children)
}

beforeEach(() => {
  vi.stubGlobal('speechSynthesis', { speak: vi.fn(), cancel: vi.fn(), speaking: false })
  vi.stubGlobal(
    'SpeechSynthesisUtterance',
    vi.fn().mockImplementation((text: string) => ({ text, lang: '' })),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders a speak button when speechSynthesis is supported', () => {
  render(createElement(SpeakButton, { text: 'answer text' }), { wrapper })
  expect(screen.getByRole('button')).toBeInTheDocument()
})

test('clicking it speaks the given text', () => {
  render(createElement(SpeakButton, { text: 'answer text' }), { wrapper })
  fireEvent.click(screen.getByRole('button'))
  expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1)
})

test('renders nothing when speechSynthesis is unsupported', () => {
  vi.unstubAllGlobals()
  const { container } = render(createElement(SpeakButton, { text: 'answer text' }), { wrapper })
  expect(container).toBeEmptyDOMElement()
})
