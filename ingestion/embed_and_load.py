"""Fetch -> parse -> chunk -> embed -> load, end to end, for every source.

Writes one SourceDocument row per chunk to Postgres and upserts the same
chunk (with its embedding) into a ChromaDB collection, so Phase 3's
retrieve node has both a keyword-searchable table and a vector index.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.db.base import AsyncSessionLocal  # noqa: E402
from app.db.models import Jurisdiction, SourceDocument  # noqa: E402

from ingestion.chunk import chunk_text  # noqa: E402
from ingestion.fetch import DEFAULT_RAW_DIR, DEFAULT_REGISTRY, fetch_all  # noqa: E402
from ingestion.parse import parse_document  # noqa: E402

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
CHROMA_BASE_URL = "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database"
CHROMA_COLLECTION = "source_chunks"

_SLUG_SAFE_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _as_date(value: str | None) -> date | None:
    """YAML gives us quoted date strings ('2026-09-15'), not date objects."""
    return date.fromisoformat(value) if value else None


def _chunk_id(doc_id: str, index: int, section_or_article: str | None) -> str:
    if section_or_article:
        safe_label = _SLUG_SAFE_RE.sub("-", section_or_article).strip("-")
        return f"{doc_id}#{safe_label}-{index:04d}"
    return f"{doc_id}#chunk-{index:04d}"


def embed_texts(texts: list[str], client: httpx.Client) -> list[list[float]]:
    resp = client.post(
        OLLAMA_EMBED_URL,
        json={"model": OLLAMA_EMBED_MODEL, "input": texts},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def get_or_create_collection(client: httpx.Client, name: str) -> str:
    """Return the collection's id, creating it if it doesn't exist yet.

    Talks to Chroma's plain REST API (v2) directly - see requirements.txt
    for why this isn't using the `chromadb` Python client package.
    """
    resp = client.post(
        f"{CHROMA_BASE_URL}/collections",
        json={"name": name, "get_or_create": True},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def chroma_upsert(
    client: httpx.Client,
    collection_id: str,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    resp = client.post(
        f"{CHROMA_BASE_URL}/collections/{collection_id}/upsert",
        json={
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas,
        },
    )
    resp.raise_for_status()


async def load_document(
    doc_id: str,
    entry: dict,
    chunks: list[dict],
    embeddings: list[list[float]],
    http_client: httpx.Client,
    collection_id: str,
) -> int:
    chroma_ids: list[str] = []
    chroma_embeddings: list[list[float]] = []
    chroma_documents: list[str] = []
    chroma_metadatas: list[dict] = []

    async with AsyncSessionLocal() as session:
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            row_id = _chunk_id(doc_id, i, chunk["section_or_article"])
            row = SourceDocument(
                id=row_id,
                doc_id=doc_id,
                title=entry["title"],
                authority=entry["authority"],
                jurisdiction=Jurisdiction(entry["jurisdiction"]),
                doc_type=entry["doc_type"],
                effective_date=_as_date(entry.get("effective_date")),
                version=entry.get("version"),
                section_or_article=chunk["section_or_article"],
                source_url=entry["source_url"],
                last_verified_date=_as_date(entry.get("last_verified_date")),
                source_text=chunk["source_text"],
            )
            await session.merge(row)

            chroma_ids.append(row_id)
            chroma_embeddings.append(vector)
            chroma_documents.append(chunk["source_text"])
            chroma_metadatas.append(
                {
                    "doc_id": doc_id,
                    "jurisdiction": entry["jurisdiction"],
                    "doc_type": entry["doc_type"],
                    "section_or_article": chunk["section_or_article"] or "",
                }
            )
        await session.commit()

    chroma_upsert(
        http_client, collection_id, chroma_ids, chroma_embeddings, chroma_documents, chroma_metadatas
    )
    return len(chunks)


async def run(registry_path: Path, raw_dir: Path) -> None:
    sources = yaml.safe_load(registry_path.read_text(encoding="utf-8"))["sources"]

    with httpx.Client(timeout=30.0) as http_client:
        collection_id = get_or_create_collection(http_client, CHROMA_COLLECTION)

        for entry in sources:
            doc_id = entry["doc_id"]
            raw_path = raw_dir / f"{doc_id}.{entry['format']}"
            print(f"[parse] {doc_id}")
            text = parse_document(raw_path, entry["format"])

            print(f"[chunk] {doc_id}")
            chunks = chunk_text(doc_id, text)
            print(f"        {len(chunks)} chunks")

            print(f"[embed] {doc_id} ({len(chunks)} chunks via {OLLAMA_EMBED_MODEL})")
            embeddings = embed_texts([c["source_text"] for c in chunks], http_client)

            print(f"[load]  {doc_id} -> Postgres + Chroma")
            n = await load_document(doc_id, entry, chunks, embeddings, http_client, collection_id)
            print(f"[done]  {doc_id}: {n} rows written")


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--skip-fetch", action="store_true", help="assume raw files already downloaded")
    args = parser.parse_args()

    if not args.skip_fetch:
        fetch_all(args.registry, args.raw_dir)

    asyncio.run(run(args.registry, args.raw_dir))
