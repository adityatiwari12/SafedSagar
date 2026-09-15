import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { useChatSession } from './useChatSession'
import { chatApi } from '../api/chatApi'

vi.mock('../api/chatApi', () => ({
  chatApi: { sendTurn: vi.fn(), escalate: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

test('sendMessage appends a user turn then an assistant turn on success', async () => {
  ;(chatApi.sendTurn as ReturnType<typeof vi.fn>).mockResolvedValue({
    conversationId: 'conv-1',
    classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
    jurisdiction: 'india',
    answer: 'answer text',
    citations: [],
    confidence: 0.7,
    confidence_band: 'medium',
    escalate_recommended: false,
  })

  const { result } = renderHook(() => useChatSession())

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

test('surfaces clarifying questions without a final answer-only flow', async () => {
  ;(chatApi.sendTurn as ReturnType<typeof vi.fn>).mockResolvedValue({
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

  const { result } = renderHook(() => useChatSession())

  await act(async () => {
    await result.current.sendMessage('vague product question')
  })

  expect(result.current.pendingClarifying).toEqual([
    'What formulation form (tablet, oil, powder)?',
  ])
})

test('changing jurisdiction re-sends the last user turn with the new jurisdiction', async () => {
  ;(chatApi.sendTurn as ReturnType<typeof vi.fn>).mockResolvedValue({
    conversationId: 'conv-1',
    classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
    jurisdiction: 'india',
    answer: 'answer text',
    citations: [],
    confidence: 0.7,
    confidence_band: 'medium',
    escalate_recommended: false,
  })

  const { result } = renderHook(() => useChatSession())
  await act(async () => {
    await result.current.sendMessage('ashwagandha patent question')
  })

  await act(async () => {
    await result.current.setJurisdiction('international')
  })

  await waitFor(() =>
    expect(chatApi.sendTurn).toHaveBeenCalledWith(
      expect.objectContaining({ jurisdiction: 'international' }),
    ),
  )
})
