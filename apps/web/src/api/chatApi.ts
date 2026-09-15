import { mockChatApi } from './mockChatApi'
import { realChatApi } from './realChatApi'

export interface ChatTurnInput {
  conversationId: string | null
  text: string
  jurisdiction: 'india' | 'international'
  answers?: Record<string, string>
  language?: 'en' | 'hi'
}

export interface Citation {
  doc_id: string
  title: string
  section_or_article?: string
  source_url?: string
  last_verified_date?: string
}

export interface ChatTurnResponse {
  conversationId: string
  clarifying_questions?: string[]
  classification: { product_type: string; ip_type: string }
  jurisdiction: 'india' | 'international'
  answer: string
  citations: Citation[]
  confidence: number
  confidence_band: 'high' | 'medium' | 'low'
  escalate_recommended: boolean
  next_steps?: string[]
  abs_tk_flags?: {
    biological_resource_likely: boolean
    traditional_knowledge_likely: boolean
    note?: string
  }
}

export interface ChatApi {
  sendTurn(input: ChatTurnInput): Promise<ChatTurnResponse>
  escalate(conversationId: string): Promise<{ escalation_id: string }>
}

const useMock = import.meta.env.VITE_USE_MOCK_CHAT !== 'false'

export const chatApi: ChatApi = useMock ? mockChatApi : realChatApi
