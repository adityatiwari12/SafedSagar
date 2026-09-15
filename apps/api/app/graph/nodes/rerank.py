"""Fuse the vector and BM25 candidate lists into one ranked list via
Reciprocal Rank Fusion (RRF) - simple, no extra model/dependency needed,
and works well for combining two differently-scaled ranking signals.
"""

from __future__ import annotations

from app.graph.state import GraphState, RetrievedChunk

RRF_K = 60
FINAL_TOP_K = 8


def rerank(state: GraphState) -> dict:
    vector_candidates = state.get("vector_candidates", [])
    bm25_candidates = state.get("bm25_candidates", [])

    scores: dict[str, float] = {}
    chunks_by_id: dict[str, RetrievedChunk] = {}

    for rank, chunk in enumerate(vector_candidates):
        scores[chunk["id"]] = scores.get(chunk["id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        chunks_by_id[chunk["id"]] = chunk

    for rank, chunk in enumerate(bm25_candidates):
        scores[chunk["id"]] = scores.get(chunk["id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        chunks_by_id.setdefault(chunk["id"], chunk)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    reranked_chunks = [chunks_by_id[cid] for cid in ranked_ids[:FINAL_TOP_K]]

    return {"reranked_chunks": reranked_chunks}
