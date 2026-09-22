"""Pydantic schemas for /chat and /escalations - the contract the
frontend's realChatApi.ts already expects (apps/web/src/api/chatApi.ts),
built ahead of a backend implementation and gated behind
VITE_USE_MOCK_CHAT. This is that implementation."""

from pydantic import BaseModel


class ChatTurnRequest(BaseModel):
    conversationId: str | None = None
    text: str
    jurisdiction: str = "india"  # "india" | "international"
    answers: dict[str, str] | None = None
    language: str | None = None
    # Optional Product dossier this turn is about (app/products/router.py).
    # Must be a product the caller owns or shares an organization with -
    # validated in app.chat.router._resolve_authorized_product.
    productId: str | None = None


class ClassificationOut(BaseModel):
    product_type: str
    ip_type: str


class CitationOut(BaseModel):
    doc_id: str
    title: str
    section_or_article: str | None = None
    source_url: str | None = None
    last_verified_date: str | None = None


class AbsTkFlagsOut(BaseModel):
    biological_resource_likely: bool
    traditional_knowledge_likely: bool
    note: str | None = None


class AnsweredByOut(BaseModel):
    provider: str  # "ollama" | "cloud"
    model: str
    fallback_used: bool = False


class RelatedProvisionOut(BaseModel):
    """A provision the legal knowledge graph connects to this answer
    (app/kg/expand.py) - shown in a "Related provisions" panel, whether or
    not the answer cited it. `via` explains the graph path and its
    provenance, e.g. "Traditional knowledge --RELATES_TO--> The Patents
    Act, 1970 - Section 3 [curated; source: ipindia-patents-act-1970 3]"."""

    doc_id: str
    title: str
    section_or_article: str | None = None
    jurisdiction: str | None = None
    relation: str
    via: str
    source_url: str | None = None


class ChatTurnResponse(BaseModel):
    conversationId: str
    clarifying_questions: list[str] | None = None
    classification: ClassificationOut
    jurisdiction: str
    answer: str
    citations: list[CitationOut]
    confidence: float
    confidence_band: str
    escalate_recommended: bool
    next_steps: list[str] | None = None
    abs_tk_flags: AbsTkFlagsOut | None = None
    # Multilingual fields (task Section 6/9) - additive, all default to
    # values that preserve today's English-only behavior unchanged when
    # `language` isn't set on the request.
    detected_language: str = "en"
    canonical_query: str | None = None
    canonical_answer: str | None = None
    translation_status: str = "not_needed"
    needs_human_review: bool = False
    # Per-node wall time in ms (node function name -> ms), e.g.
    # {"retrieve": 210.4, "reason_and_cite": 25890.2} - debugging/tuning
    # aid for RAG latency, not shown by default in the UI.
    timing_ms: dict[str, float] | None = None
    # Which provider/model actually produced this answer (see
    # app/llm/generate.py's get_last_call_metadata) - None on turns that
    # short-circuit before reason_and_cite runs (out-of-scope refusal,
    # clarifying-question turns).
    answered_by: AnsweredByOut | None = None
    # Knowledge-graph neighbours of this answer (app/kg/expand.py) -
    # additive; empty on turns that don't reach expand_with_graph.
    related_provisions: list[RelatedProvisionOut] = []
    # True when this turn folded prior turns of the conversation into the
    # graph's question (chat/router.py's history_text) - i.e. a follow-up
    # like "what about internationally?" was actually resolved using what
    # was asked/answered earlier, not read in isolation.
    used_conversation_context: bool = False


class EscalateRequest(BaseModel):
    conversationId: str


class EscalateResponse(BaseModel):
    escalation_id: str


class ConversationSummaryOut(BaseModel):
    conversationId: str
    title: str
    language: str | None = None
    created_at: str
    updated_at: str


class ConversationMessageOut(BaseModel):
    role: str  # "user" | "assistant"
    display_text: str
    language: str | None = None
    created_at: str
    # Populated for assistant messages only - the full response this turn
    # produced, so the history view re-renders identically to when it was
    # first shown (citations, classification, confidence and all).
    response: ChatTurnResponse | None = None
