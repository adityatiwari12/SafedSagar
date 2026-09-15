"""Deterministic unit tests for the pure (non-network) graph nodes."""

from app.graph.nodes.escalate_if_needed import escalate_if_needed
from app.graph.nodes.rerank import rerank
from app.graph.nodes.score_confidence import score_confidence
from app.graph.nodes.validate_citations import validate_citations


def _chunk(id_: str, doc_id: str = "doc-1", section: str | None = "1") -> dict:
    return {
        "id": id_,
        "doc_id": doc_id,
        "doc_type": "statute",
        "section_or_article": section,
        "source_text": "text",
        "title": "title",
        "source_url": "url",
    }


def test_rerank_fuses_and_dedupes_by_rrf():
    vector_candidates = [_chunk("a"), _chunk("b"), _chunk("c")]
    bm25_candidates = [_chunk("b"), _chunk("a"), _chunk("d")]

    result = rerank({"vector_candidates": vector_candidates, "bm25_candidates": bm25_candidates})
    ids = [c["id"] for c in result["reranked_chunks"]]

    # "a" and "b" appear in both lists (near the top of each) so RRF
    # should rank them above chunks appearing in only one list.
    assert ids[0] in ("a", "b")
    assert ids[1] in ("a", "b")
    assert set(ids) == {"a", "b", "c", "d"}
    assert len(ids) == len(set(ids))  # no duplicates


def test_rerank_respects_top_k():
    vector_candidates = [_chunk(f"v{i}") for i in range(20)]
    result = rerank({"vector_candidates": vector_candidates, "bm25_candidates": []})
    assert len(result["reranked_chunks"]) <= 8


def test_validate_citations_accepts_exact_match():
    retrieved = [_chunk("x", doc_id="patents-act", section="3")]
    raw_citations = [{"doc_id": "patents-act", "section_or_article": "3"}]

    result = validate_citations({"reranked_chunks": retrieved, "raw_citations": raw_citations})

    assert result["validated_citations"] == raw_citations
    assert result["rejected_citations"] == []


def test_validate_citations_rejects_fabricated_citation():
    retrieved = [_chunk("x", doc_id="patents-act", section="3")]
    raw_citations = [
        {"doc_id": "patents-act", "section_or_article": "3"},  # real
        {"doc_id": "patents-act", "section_or_article": "99"},  # fabricated section
        {"doc_id": "made-up-act", "section_or_article": "1"},  # fabricated doc
    ]

    result = validate_citations({"reranked_chunks": retrieved, "raw_citations": raw_citations})

    assert result["validated_citations"] == [raw_citations[0]]
    assert result["rejected_citations"] == raw_citations[1:]


def test_validate_citations_empty_inputs():
    result = validate_citations({"reranked_chunks": [], "raw_citations": []})
    assert result == {"validated_citations": [], "rejected_citations": []}


def test_score_confidence_zero_when_nothing_retrieved():
    result = score_confidence({"reranked_chunks": [], "validated_citations": [], "rejected_citations": []})
    assert result == {"confidence_score": 0.0, "confidence_level": "low"}


def test_score_confidence_high_when_all_citations_validated():
    chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
    validated = [{"doc_id": "doc-1", "section_or_article": "1"}] * 3
    result = score_confidence({"reranked_chunks": chunks, "validated_citations": validated, "rejected_citations": []})
    assert result["confidence_level"] == "high"
    assert result["confidence_score"] == 1.0


def test_score_confidence_low_when_all_citations_rejected():
    chunks = [_chunk("a")]
    rejected = [{"doc_id": "doc-1", "section_or_article": "1"}] * 3
    result = score_confidence({"reranked_chunks": chunks, "validated_citations": [], "rejected_citations": rejected})
    assert result["confidence_level"] == "low"


def test_escalate_when_confidence_low():
    result = escalate_if_needed({"confidence_level": "low", "validated_citations": [], "product_classification": "cosmetic"})
    assert result["escalate"] is True
    assert result["escalation_reason"]


def test_escalate_when_no_validated_citations():
    result = escalate_if_needed({"confidence_level": "medium", "validated_citations": [], "product_classification": "cosmetic"})
    assert result["escalate"] is True


def test_escalate_when_product_unclear():
    citations = [{"doc_id": "doc-1", "section_or_article": "1"}]
    result = escalate_if_needed({"confidence_level": "high", "validated_citations": citations, "product_classification": "unclear"})
    assert result["escalate"] is True


def test_no_escalation_when_confident_cited_and_classified():
    citations = [{"doc_id": "doc-1", "section_or_article": "1"}]
    result = escalate_if_needed({"confidence_level": "high", "validated_citations": citations, "product_classification": "cosmetic"})
    assert result == {"escalate": False, "escalation_reason": None}
