"""Deterministic unit tests for the pure (non-network) graph nodes."""

from app.graph.nodes.rerank import rerank
from app.graph.nodes.validate_citations import validate_citations


def _chunk(id_: str, doc_id: str = "doc-1", section: str | None = "1") -> dict:
    return {
        "id": id_,
        "doc_id": doc_id,
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
