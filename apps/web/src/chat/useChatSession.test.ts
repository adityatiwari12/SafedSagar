import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, expect, test, vi } from 'vitest'
import { useChatSession } from './useChatSession'
import { chatApi } from '../api/chatApi'
import { LanguageProvider } from '../i18n/LanguageContext'

vi.mock('../api/chatApi', () => ({
  chatApi: { sendTurn: vi.fn(), sendTurnStreaming: vi.fn(), escalate: vi.fn() },
}))

function wrapper(props: { children: ReactNode }) {
  return createElement(LanguageProvider, null, props.children)
}

beforeEach(() => {
  vi.clearAllMocks()
})

test('sendMessage appends a user turn then an assistant turn on success', async () => {
  ;(chatApi.sendTurnStreaming as ReturnType<typeof vi.fn>).mockResolvedValue({
    conversationId: 'conv-1',
    classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
    jurisdiction: 'india',
    answer: 'answer text',
    citations: [],
    confidence: 0.7,
    confidence_band: 'medium',
    escalate_recommended: false,
  })

  const { result } = renderHook(() => useChatSession(), { wrapper })

  await act(async () => {
    await result.current.sendMessage('ashwagandha patent question')
  })

  expect(result.current.turns).toHaveLength(2)
  expect(result.current.turns[0]).toMatchObject({
    role: 'user',
    text: 'ashwagandha patent question',
  })
  expect(result.current.turns[1]).toMatchObject({ role: 'assistant' })
  expect(result.current.status).toBe('idle')
})

test('a clarifying_questions response becomes a normal turn, not a blocking form', async () => {
  ;(chatApi.sendTurnStreaming as ReturnType<typeof vi.fn>).mockResolvedValue({
    conversationId: 'conv-1',
    clarifying_questions: ['What formulation form (tablet, oil, powder)?'],
    classification: { product_type: 'unknown', ip_type: 'unknown' },
    jurisdiction: 'india',
    answer: '',
    citations: [],
    confidence: 0.3,
    confidence_band: 'low',
    escalate_recommended: false,
  })

  const { result } = renderHook(() => useChatSession(), { wrapper })

  await act(async () => {
    await result.current.sendMessage('vague product question')
  })

  // Pushed as an ordinary assistant turn carrying the full response (so the
  // UI can render the question), not diverted into pendingClarifying.
  expect(result.current.turns).toHaveLength(2)
  expect(result.current.turns[1]).toMatchObject({ role: 'assistant' })
  expect(result.current.turns[1].response?.clarifying_questions).toEqual([
    'What formulation form (tablet, oil, powder)?',
  ])
  expect(result.current.pendingClarifying).toBeNull()
  expect(result.current.status).toBe('idle')
})

test('the next round is a plain sendMessage(text) call, with no answers payload', async () => {
  ;(chatApi.sendTurnStreaming as ReturnType<typeof vi.fn>)
    .mockResolvedValueOnce({
      conversationId: 'conv-1',
      clarifying_questions: ['What formulation form (tablet, oil, powder)?'],
      classification: { product_type: 'unknown', ip_type: 'unknown' },
      jurisdiction: 'india',
      answer: '',
      citations: [],
      confidence: 0.3,
      confidence_band: 'low',
      escalate_recommended: false,
    })
    .mockResolvedValueOnce({
      conversationId: 'conv-1',
      classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
      jurisdiction: 'india',
      answer: 'Tablets made from ashwagandha extract are...',
      citations: [],
      confidence: 0.7,
      confidence_band: 'medium',
      escalate_recommended: false,
    })

  const { result } = renderHook(() => useChatSession(), { wrapper })

  await act(async () => {
    await result.current.sendMessage('vague product question')
  })
  await act(async () => {
    await result.current.sendMessage('It is a tablet made from ashwagandha extract')
  })

  expect(chatApi.sendTurnStreaming).toHaveBeenLastCalledWith(
    expect.objectContaining({
      text: 'It is a tablet made from ashwagandha extract',
      conversationId: 'conv-1',
      answers: undefined,
    }),
    expect.any(Function),
  )
  expect(result.current.turns).toHaveLength(4)
  expect(result.current.turns[3]).toMatchObject({ role: 'assistant' })
  expect(result.current.turns[3].response?.answer).toBe('Tablets made from ashwagandha extract are...')
  expect(result.current.pendingClarifying).toBeNull()
})

test('changing jurisdiction re-sends the last user turn with the new jurisdiction', async () => {
  ;(chatApi.sendTurnStreaming as ReturnType<typeof vi.fn>).mockResolvedValue({
    conversationId: 'conv-1',
    classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
    jurisdiction: 'india',
    answer: 'answer text',
    citations: [],
    confidence: 0.7,
    confidence_band: 'medium',
    escalate_recommended: false,
  })

  const { result } = renderHook(() => useChatSession(), { wrapper })
  await act(async () => {
    await result.current.sendMessage('ashwagandha patent question')
  })

  await act(async () => {
    await result.current.setJurisdiction('international')
  })

  await waitFor(() =>
    expect(chatApi.sendTurnStreaming).toHaveBeenCalledWith(
      expect.objectContaining({ jurisdiction: 'international' }),
      expect.any(Function),
    ),
  )
})

test('includes the active product id on turns while a product is set, and stops once dismissed', async () => {
  ;(chatApi.sendTurnStreaming as ReturnType<typeof vi.fn>).mockResolvedValue({
    conversationId: 'conv-1',
    classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
    jurisdiction: 'india',
    answer: 'answer text',
    citations: [],
    confidence: 0.7,
    confidence_band: 'medium',
    escalate_recommended: false,
  })

  const { result } = renderHook(() => useChatSession(), { wrapper })

  act(() => {
    result.current.setActiveProduct({ id: 'p1', name: 'Ashwagandha capsules' })
  })

  await act(async () => {
    await result.current.sendMessage('About my product')
  })

  expect(chatApi.sendTurnStreaming).toHaveBeenLastCalledWith(
    expect.objectContaining({ productId: 'p1' }),
    expect.any(Function),
  )

  act(() => {
    result.current.setActiveProduct(null)
  })

  await act(async () => {
    await result.current.sendMessage('A follow-up with no product')
  })

  expect(chatApi.sendTurnStreaming).toHaveBeenLastCalledWith(
    expect.objectContaining({ productId: null }),
    expect.any(Function),
  )
})
