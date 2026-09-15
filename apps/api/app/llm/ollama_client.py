"""Thin sync wrapper around Ollama's local HTTP API - embeddings and
generation. No LangChain LLM abstraction: the graph nodes call these
functions directly, since Ollama's API is already simple enough that an
adapter layer would just be indirection.
"""

from __future__ import annotations

import json

import httpx

from app.config import settings


def embed(texts: list[str]) -> list[list[float]]:
    """Embed one or more texts via Ollama's configured embedding model."""
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/embed",
        json={"model": settings.ollama_embed_model, "input": texts},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def generate_json(prompt: str, timeout: float = 120.0, *, model: str | None = None) -> dict:
    """Generate a response constrained to JSON output (Ollama's `format:
    "json"` mode) and parse it. Raises json.JSONDecodeError if the model
    still produced something unparseable - callers should not assume a
    local, non-instruction-tuned-for-JSON model always succeeds.

    Uses /api/chat (a user-role message), not /api/generate (a raw
    completion prompt). Verified live (2026-09-15): the same instruction
    sent as a raw /api/generate prompt got gpt-oss:20b confused into
    echoing the instruction back as malformed JSON; sent as a proper
    /api/chat message it returned clean, valid JSON on the first try.
    Chat-tuned instruction/reasoning models expect their chat template
    applied via the messages API - /api/generate skips that.
    """
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": model or settings.ollama_generate_model,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    raw_response = resp.json()["message"]["content"]
    return json.loads(raw_response)
