"""Pydantic schemas for the /query endpoint."""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    jurisdiction: str | None = None  # "india" | "international"
    doc_type: str | None = None


class CitationOut(BaseModel):
    doc_id: str
    section_or_article: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    rejected_citation_count: int
