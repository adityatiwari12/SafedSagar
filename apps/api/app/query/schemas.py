"""Pydantic schemas for the /query endpoint."""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    jurisdiction: str | None = None  # "india" | "international" - explicit switch (FR-04); inferred if omitted
    doc_type: str | None = None


class CitationOut(BaseModel):
    doc_id: str
    section_or_article: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    rejected_citation_count: int

    product_classification: str
    jurisdiction: str | None
    jurisdiction_source: str
    ip_types: list[str]

    confidence_score: float
    confidence_level: str
    escalate: bool
    escalation_reason: str | None
