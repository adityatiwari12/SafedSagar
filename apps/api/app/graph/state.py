"""Shared state threaded through the LangGraph retrieval/citation graph."""

from __future__ import annotations

from typing import TypedDict


class RetrievedChunk(TypedDict):
    """One chunk as returned by retrieve/rerank - matches a
    source_documents row's citable fields."""

    id: str
    doc_id: str
    doc_type: str
    section_or_article: str | None
    source_text: str
    title: str
    source_url: str


class Citation(TypedDict):
    doc_id: str
    section_or_article: str | None


class GraphState(TypedDict, total=False):
    question: str  # the latest turn's raw text, unmodified
    history_text: str | None  # prior turns as "User:...\nAssistant:...\n" lines, or None
    retrieval_query: str  # condense_query's standalone rewrite - what classify/route/retrieve use
    jurisdiction: str | None  # "india" | "international" | None (both)
    doc_type: str | None

    product_classification: str  # one of PRODUCT_CATEGORIES, or "unclear"
    jurisdiction_source: str  # "explicit" (caller provided it) | "inferred"
    ip_types: list[str]  # subset of IP_TYPES

    vector_candidates: list[RetrievedChunk]
    bm25_candidates: list[RetrievedChunk]
    reranked_chunks: list[RetrievedChunk]

    answer: str
    raw_citations: list[Citation]
    validated_citations: list[Citation]
    rejected_citations: list[Citation]
    next_steps: list[str]

    confidence_score: float  # 0.0-1.0
    confidence_level: str  # "high" | "medium" | "low"
    escalate: bool
    escalation_reason: str | None

    node_timings: dict[str, float]  # node function name -> wall time in ms


# PRD Section "Description - Detailed Description": the six formulation
# categories the assistant classifies a product into before giving
# category-specific IP/regulatory guidance.
PRODUCT_CATEGORIES = [
    "classical_or_generic_medicine",
    "patent_or_proprietary_medicine",
    "new_or_non_classical_drug",
    "phytopharmaceutical",
    "ayurveda_aahara_or_nutraceutical",
    "cosmetic",
    "unclear",
]

# CLAUDE.md/PRD: the IP regimes an Ayurvedic product can touch.
IP_TYPES = [
    "patent",
    "trademark",
    "geographical_indication",
    "copyright",
    "design",
    "trade_secret",
    "plant_variety",
    "access_and_benefit_sharing",
    "drug_regulatory",
]
