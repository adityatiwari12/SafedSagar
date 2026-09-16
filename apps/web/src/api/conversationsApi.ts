import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'
import { ChatTurnResponse } from './chatApi'
import { LanguageCode } from './languages'

export interface ConversationSummary {
  conversationId: string
  title: string
  language: LanguageCode | null
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  display_text: string
  language: LanguageCode | null
  created_at: string
  response: ChatTurnResponse | null
}

export const conversationsApi = {
  list(): Promise<ConversationSummary[]> {
    return apiFetch<ConversationSummary[]>('/conversations', { method: 'GET' }, getStoredToken())
  },

  getMessages(conversationId: string): Promise<ConversationMessage[]> {
    return apiFetch<ConversationMessage[]>(
      `/conversations/${conversationId}/messages`,
      { method: 'GET' },
      getStoredToken(),
    )
  },

  remove(conversationId: string): Promise<void> {
    return apiFetch<void>(`/conversations/${conversationId}`, { method: 'DELETE' }, getStoredToken())
  },
}
