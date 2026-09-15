import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'
import { ChatApi, ChatTurnInput, ChatTurnResponse } from './chatApi'

export const realChatApi: ChatApi = {
  sendTurn(input: ChatTurnInput): Promise<ChatTurnResponse> {
    return apiFetch<ChatTurnResponse>(
      '/chat',
      { method: 'POST', body: JSON.stringify(input) },
      getStoredToken(),
    )
  },

  escalate(conversationId: string): Promise<{ escalation_id: string }> {
    return apiFetch<{ escalation_id: string }>(
      '/escalations',
      { method: 'POST', body: JSON.stringify({ conversationId }) },
      getStoredToken(),
    )
  },
}
