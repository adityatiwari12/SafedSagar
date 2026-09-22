import { mockChatApi } from './mockChatApi'
import { realChatApi } from './realChatApi'
import { LanguageCode } from './languages'

export interface ChatTurnInput {
  conversationId: string | null
  text: string
  jurisdiction: 'india' | 'international'
  answers?: Record<string, string>
  language?: LanguageCode
  // Product dossier this turn is scoped to, if any - the Case this turn
  // creates gets linked to it server-side. null/undefined means unscoped.
  productId?: string | null
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
  // Provenance of the LLM call that produced this answer - additive, not
  // present on every historical row (e.g. out-of-scope short-circuits
  // never call an LLM, so this comes back null there).
  answered_by?: { provider: string; model: string; fallback_used: boolean } | null
  // Knowledge-graph neighbourhood of the cited evidence - adjacent legal
  // context the answer did not necessarily cite. Never conflate with
  // `citations` above: those are what the answer actually drew on.
  related_provisions?: RelatedProvision[]
  // True when this turn's reasoning drew on earlier messages in the same
  // conversation (condense_query folded prior context into the query).
  used_conversation_context?: boolean
}

export interface RelatedProvision {
  doc_id: string
  title: string
  section_or_article?: string | null
  jurisdiction: 'india' | 'international'
  relation: string
  via: string
  source_url?: string | null
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
