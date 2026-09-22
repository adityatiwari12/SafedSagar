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


def generate_json(
    prompt: str,
    timeout: float = 120.0,
    *,
    model: str | None = None,
    think: str | bool | None = None,
    keep_alive: str | None = None,
) -> dict:
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

    `think`: for thinking models (e.g. gpt-oss), the reasoning-effort
    level ("low"/"medium"/"high") or a bool to force it on/off. Verified
    live (2026-09-15) on gpt-oss:20b/CPU: "low" cut a trivial warm call
    from ~44s to ~3.5s while still returning valid JSON - `think: false`
    instead skips the reasoning channel entirely and broke JSON validity,
    so this is the real lever, not disabling thinking. On a realistic
    multi-chunk reasoning prompt "low" still costs ~55s (CPU token decode
    itself, not the thinking phase, dominates once the answer is long) -
    still not free, but consistently better than the unset default.

    `keep_alive`: how long Ollama keeps the model resident after this
    call (e.g. "30m"). Ollama's default unload window is 5 minutes; worth
    raising for a large model (gpt-oss:20b takes ~20-40s to reload from
    disk) used across a multi-turn conversation with gaps between turns.
    """
    body: dict = {
        "model": model or settings.ollama_generate_model,
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"num_ctx": settings.ollama_num_ctx},
    }
    if think is not None:
        body["think"] = think
    if keep_alive is not None:
        body["keep_alive"] = keep_alive

    resp = httpx.post(
        f"{settings.ollama_base_url}/api/chat",
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    raw_response = resp.json()["message"]["content"]
    return json.loads(raw_response)
