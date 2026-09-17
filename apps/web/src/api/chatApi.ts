import { mockChatApi } from './mockChatApi'
import { realChatApi } from './realChatApi'
import { LanguageCode } from './languages'

export interface ChatTurnInput {
  conversationId: string | null
  text: string
  jurisdiction: 'india' | 'international'
  answers?: Record<string, string>
  language?: LanguageCode
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
  // Multilingual fields - additive, backend defaults them so English-only
  // callers see unchanged behavior (detected_language: "en",
  // translation_status: "not_needed").
  detected_language?: LanguageCode
  canonical_query?: string | null
  canonical_answer?: string | null
  translation_status?: 'not_needed' | 'verified' | 'failed' | 'unavailable'
  needs_human_review?: boolean
}

// Matches chat/router.py's NODE_TO_STEP values - the JourneyStepper step
// ids a live /chat/ws turn can report progress against, in true backend
// execution order (not the order a hand-authored UI label list would
// guess at).
export type JourneyStepId =
  | 'language'
  | 'understand'
  | 'classify'
  | 'jurisdiction'
  | 'need'
  | 'abs'
  | 'answer'
  | 'action'

export interface ChatApi {
  sendTurn(input: ChatTurnInput): Promise<ChatTurnResponse>
  // Same contract as sendTurn, but calls onStep as each pipeline stage
  // actually completes (real backend progress over /chat/ws) instead of
  // resolving only once the whole turn is done. onStep may fire zero
  // times before resolving (e.g. an out-of-scope question short-circuits
  // after just "classify").
  sendTurnStreaming(input: ChatTurnInput, onStep: (step: JourneyStepId) => void): Promise<ChatTurnResponse>
  escalate(conversationId: string): Promise<{ escalation_id: string }>
}

const useMock = import.meta.env.VITE_USE_MOCK_CHAT !== 'false'

export const chatApi: ChatApi = useMock ? mockChatApi : realChatApi
