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


class EscalateRequest(BaseModel):
    conversationId: str


class EscalateResponse(BaseModel):
    escalation_id: str
