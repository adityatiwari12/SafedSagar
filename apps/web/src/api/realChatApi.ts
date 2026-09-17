import { ApiError, apiFetch, apiWsUrl } from './http'
import { getStoredToken } from '../auth/AuthContext'
import { ChatApi, ChatTurnInput, ChatTurnResponse, JourneyStepId } from './chatApi'

export const realChatApi: ChatApi = {
  sendTurn(input: ChatTurnInput): Promise<ChatTurnResponse> {
    return apiFetch<ChatTurnResponse>(
      '/chat',
      { method: 'POST', body: JSON.stringify(input) },
      getStoredToken(),
    )
  },

  sendTurnStreaming(input: ChatTurnInput, onStep: (step: JourneyStepId) => void): Promise<ChatTurnResponse> {
    return new Promise((resolve, reject) => {
      const token = getStoredToken()
      const url = apiWsUrl('/chat/ws') + (token ? `?token=${encodeURIComponent(token)}` : '')
      const ws = new WebSocket(url)
      let settled = false

      const finish = (fn: () => void) => {
        if (settled) return
        settled = true
        fn()
        ws.close()
      }

      ws.onopen = () => ws.send(JSON.stringify(input))

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data as string)
        if (msg.type === 'step') {
          onStep(msg.step as JourneyStepId)
        } else if (msg.type === 'result') {
          finish(() => resolve(msg.data as ChatTurnResponse))
        } else if (msg.type === 'error') {
          finish(() => reject(new ApiError(500, msg.message)))
        }
      }

      // Covers both a handshake failure (onerror) and the server closing
      // the socket without ever sending a result/error frame (onclose) -
      // e.g. resolve_user_from_token rejecting the token, which closes
      // with 4401 before any JSON frame is sent.
      ws.onerror = () => finish(() => reject(new ApiError(0, 'WebSocket connection failed')))
      ws.onclose = (event) => {
        if (settled) return
        settled = true
        reject(new ApiError(event.code, event.reason || 'Connection closed before a response was received'))
      }
    })
  },

  escalate(conversationId: string): Promise<{ escalation_id: string }> {
    return apiFetch<{ escalation_id: string }>(
      '/escalations',
      { method: 'POST', body: JSON.stringify({ conversationId }) },
      getStoredToken(),
    )
  },
}
