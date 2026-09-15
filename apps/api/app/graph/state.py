"""Shared state threaded through the LangGraph retrieval/citation graph."""

from __future__ import annotations

from typing import TypedDict


class RetrievedChunk(TypedDict):
    """One chunk as returned by retrieve/rerank - matches a
    source_documents row's citable fields."""

    id: str
    doc_id: str
    section_or_article: str | None
    source_text: str
    title: str
    source_url: str


class Citation(TypedDict):
    doc_id: str
    section_or_article: str | None


class GraphState(TypedDict, total=False):
    question: str
    jurisdiction: str | None  # "india" | "international" | None (both)
    doc_type: str | None

    vector_candidates: list[RetrievedChunk]
    bm25_candidates: list[RetrievedChunk]
    reranked_chunks: list[RetrievedChunk]

    answer: str
    raw_citations: list[Citation]
    validated_citations: list[Citation]
    rejected_citations: list[Citation]
