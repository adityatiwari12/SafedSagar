import { expect, test } from 'vitest'
import { mockChatApi } from './mockChatApi'

test('recognizes an ashwagandha patent question as India patent, medium confidence', async () => {
  const response = await mockChatApi.sendTurn({
    conversationId: null,
    text: 'I developed a new Ayurvedic formulation using Ashwagandha. Can I patent it?',
    jurisdiction: 'india',
  })

  expect(response.classification.ip_type).toBe('patent')
  expect(response.jurisdiction).toBe('india')
  expect(response.confidence_band).toBe('medium')
  expect(response.citations.length).toBeGreaterThan(0)
  expect(response.citations[0]).toMatchObject({ doc_id: expect.any(String) })
  expect(response.conversationId).toEqual(expect.any(String))
})

test('falls back to a low-confidence generic response for unrecognized questions', async () => {
  const response = await mockChatApi.sendTurn({
    conversationId: null,
    text: 'asdkjhasdkjh nonsense query',
    jurisdiction: 'india',
  })

  expect(response.confidence_band).toBe('low')
  expect(response.escalate_recommended).toBe(true)
})

test('reuses the given conversationId across turns', async () => {
  const first = await mockChatApi.sendTurn({
    conversationId: null,
    text: 'Ashwagandha patent question',
    jurisdiction: 'india',
  })
  const second = await mockChatApi.sendTurn({
    conversationId: first.conversationId,
    text: 'follow up',
    jurisdiction: 'india',
  })

  expect(second.conversationId).toBe(first.conversationId)
})

test('escalate returns an escalation id', async () => {
  const result = await mockChatApi.escalate('conv-1')
  expect(result.escalation_id).toEqual(expect.any(String))
})
