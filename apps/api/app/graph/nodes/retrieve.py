"""Hybrid retrieval: vector similarity (Chroma) + BM25 keyword search
(Postgres), both filtered by jurisdiction/doc_type. Two separate
candidate lists are returned - fusing them into one ranked list is
rerank's job, not this node's, matching CLAUDE.md's node sequence.

BM25 indexes are cached per (jurisdiction, doc_type) filter key so Wave A
corpus growth does not rebuild the index on every query. Vector and BM25
legs run concurrently via asyncio.gather.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import httpx
from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models import SourceDocument
from app.graph.state import GraphState, RetrievedChunk
from app.llm.ollama_client import embed

_TOKEN_RE = re.compile(r"[a-z0-9]+")

VECTOR_TOP_N = 10
BM25_TOP_N = 10

# Chroma's v2 REST API takes the collection's UUID in the path, not its
# name, for /query and /count (only the collection-lookup-by-name GET
# accepts a name) - resolved once and cached, since it's stable for the
# process lifetime (ingestion creates the collection once, ahead of time).
_collection_id_cache: str | None = None


@dataclass
class _Bm25Entry:
    row_count: int
    rows: list
    tokenized: list[list[str]]
    bm25: BM25Okapi


_bm25_cache: dict[str, _Bm25Entry] = {}


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _bm25_cache_key(jurisdiction: str | None, doc_type: str | None) -> str:
    return f"{jurisdiction}|{doc_type}"


def invalidate_bm25_cache() -> None:
    """Drop all cached BM25 indexes (call after re-ingestion)."""
    _bm25_cache.clear()


async def _get_collection_id() -> str:
    global _collection_id_cache
    if _collection_id_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.chroma_base_url}/collections/{settings.chroma_collection}",
                timeout=15.0,
            )
            resp.raise_for_status()
            _collection_id_cache = resp.json()["id"]
    return _collection_id_cache


def _row_to_chunk(row: SourceDocument) -> RetrievedChunk:
    return RetrievedChunk(
        id=row.id,
        doc_id=row.doc_id,
        doc_type=row.doc_type,
        section_or_article=row.section_or_article,
        source_text=row.source_text,
        title=row.title,
        source_url=row.source_url or "",
    )


async def _filtered_rows(
    jurisdiction: str | None, doc_type: str | None
) -> list[SourceDocument]:
    async with AsyncSessionLocal() as session:
        stmt = select(SourceDocument)
        if jurisdiction:
            stmt = stmt.where(SourceDocument.jurisdiction == jurisdiction)
        if doc_type:
            stmt = stmt.where(SourceDocument.doc_type == doc_type)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _get_bm25_entry(
    jurisdiction: str | None, doc_type: str | None
) -> _Bm25Entry | None:
    key = _bm25_cache_key(jurisdiction, doc_type)
    rows = await _filtered_rows(jurisdiction, doc_type)
    if not rows:
        _bm25_cache.pop(key, None)
        return None

    cached = _bm25_cache.get(key)
    if cached is not None and cached.row_count == len(rows):
        return cached

    tokenized = [_tokenize(row.source_text) for row in rows]
    entry = _Bm25Entry(
        row_count=len(rows),
        rows=rows,
        tokenized=tokenized,
        bm25=BM25Okapi(tokenized),
    )
    _bm25_cache[key] = entry
    return entry


async def _vector_search(
    question: str, jurisdiction: str | None, doc_type: str | None
) -> list[RetrievedChunk]:
    query_vector = (await asyncio.to_thread(embed, [question]))[0]

    where_clauses = []
    if jurisdiction:
        where_clauses.append({"jurisdiction": jurisdiction})
    if doc_type:
        where_clauses.append({"doc_type": doc_type})
    where = None
    if len(where_clauses) == 1:
        where = where_clauses[0]
    elif len(where_clauses) > 1:
        where = {"$and": where_clauses}

    body = {"query_embeddings": [query_vector], "n_results": VECTOR_TOP_N}
    if where:
        body["where"] = where

    collection_id = await _get_collection_id()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.chroma_base_url}/collections/{collection_id}/query",
            json=body,
            timeout=30.0,
        )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ids") or not data["ids"][0]:
        return []

    # Chroma's own metadata copy only carries what ingestion put there for
    # filtering (doc_id/jurisdiction/doc_type/section_or_article), not the
    # full citation fields - Postgres is the authoritative row, so hydrate
    # from there instead of trusting a second copy of the same data.
    chunk_ids = data["ids"][0]
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SourceDocument).where(SourceDocument.id.in_(chunk_ids))
        )
        rows_by_id = {row.id: row for row in result.scalars().all()}

    return [_row_to_chunk(rows_by_id[cid]) for cid in chunk_ids if cid in rows_by_id]


async def _bm25_search(
    question: str, jurisdiction: str | None, doc_type: str | None
) -> list[RetrievedChunk]:
    entry = await _get_bm25_entry(jurisdiction, doc_type)
    if entry is None:
        return []
    scores = entry.bm25.get_scores(_tokenize(question))
    ranked = sorted(zip(entry.rows, scores), key=lambda pair: pair[1], reverse=True)
    return [_row_to_chunk(row) for row, score in ranked[:BM25_TOP_N] if score > 0]


async def retrieve(state: GraphState) -> dict:
    question = state["retrieval_query"]
    jurisdiction = state.get("jurisdiction")
    doc_type = state.get("doc_type")

    vector_candidates, bm25_candidates = await asyncio.gather(
        _vector_search(question, jurisdiction, doc_type),
        _bm25_search(question, jurisdiction, doc_type),
    )
    return {
        "vector_candidates": vector_candidates,
        "bm25_candidates": bm25_candidates,
    }
