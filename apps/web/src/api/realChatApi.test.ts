import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { realChatApi } from './realChatApi'
import { ChatTurnResponse } from './chatApi'

const BASE_RESPONSE: ChatTurnResponse = {
  conversationId: 'conv-1',
  classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
  jurisdiction: 'india',
  answer: 'answer text',
  citations: [],
  confidence: 0.7,
  confidence_band: 'medium',
  escalate_recommended: false,
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  localStorage.clear()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

test('sendTurn includes productId in the POST body when supplied', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => BASE_RESPONSE,
  })

  await realChatApi.sendTurn({
    conversationId: null,
    text: 'About my product',
    jurisdiction: 'india',
    productId: 'p1',
  })

  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/chat')
  expect(JSON.parse(init.body)).toMatchObject({ productId: 'p1' })
})

test('sendTurn omits productId from the body when not supplied', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => BASE_RESPONSE,
  })

  await realChatApi.sendTurn({
    conversationId: null,
    text: 'A question with no product',
    jurisdiction: 'india',
  })

  const [, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(JSON.parse(init.body).productId).toBeUndefined()
})

// Fake WebSocket - captures what realChatApi.sendTurnStreaming sends over
// the socket and lets the test drive open/message events, since jsdom has
// no real WebSocket server to talk to.
class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: ((event: { code: number; reason: string }) => void) | null = null

  constructor(public url: string) {
    FakeWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {}
}

test('sendTurnStreaming sends productId in the initial WebSocket frame', async () => {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket as unknown as typeof WebSocket)

  const onStep = vi.fn()
  const resultPromise = realChatApi.sendTurnStreaming(
    {
      conversationId: null,
      text: 'About my product',
      jurisdiction: 'india',
      productId: 'p1',
    },
    onStep,
  )

  const ws = FakeWebSocket.instances[0]
  ws.onopen?.()
  expect(JSON.parse(ws.sent[0])).toMatchObject({ productId: 'p1' })

  ws.onmessage?.({ data: JSON.stringify({ type: 'result', data: BASE_RESPONSE }) })
  const result = await resultPromise
  expect(result.conversationId).toBe('conv-1')
})
