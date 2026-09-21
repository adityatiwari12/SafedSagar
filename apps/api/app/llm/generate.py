"""Facade for JSON generation - routes to Ollama (default) or cloud Llama.

Observability: `generate_json`'s return value stays a plain dict (every
existing caller - classify_product, condense_query, route_jurisdiction,
route_ip_type, reason_and_cite - unpacks it directly and shouldn't have to
change). Which provider/model actually answered a given call, and whether
a cloud failure fell back to local Ollama, is exposed separately via
`get_last_call_metadata()`, backed by a ContextVar set immediately before
`generate_json` returns (or raises). A caller that cares - currently just
the /chat route, for `ChatTurnResponse.answered_by` - calls it right after
`generate_json()` returns, in the same call stack. A ContextVar (rather
than a plain module global) means concurrent requests handled on
different threads/async tasks don't clobber each other's last-call info.
This was chosen over threading the metadata through every caller's return
value/signature, which would touch five call sites for a value only one
of them (the top-level chat response) actually needs.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass

from app.config import settings
from app.llm import cloud_client, ollama_client

logger = logging.getLogger(__name__)

ollama_generate_json = ollama_client.generate_json
cloud_generate_json = cloud_client.generate_json


@dataclass(frozen=True)
class CallMetadata:
    provider: str  # "ollama" | "cloud"
    model: str
    fallback_used: bool = False


_last_call_metadata: ContextVar["CallMetadata | None"] = ContextVar(
    "_llm_last_call_metadata", default=None
)


def get_last_call_metadata() -> "CallMetadata | None":
    """Provider/model that actually served the most recent `generate_json`
    call in this context (thread or async task), or None if none has run
    yet in it. See module docstring for why this is a ContextVar rather
    than a return value."""
    return _last_call_metadata.get()


def generate_json(
    prompt: str,
    timeout: float = 120.0,
    *,
    provider: str | None = None,
    model: str | None = None,
    think: str | bool | None = None,
    keep_alive: str | None = None,
) -> dict:
    chosen = (provider or settings.llm_provider or "ollama").lower()

    if chosen == "cloud":
        try:
            result = cloud_generate_json(prompt, timeout=timeout)
        except Exception as exc:
            if not settings.llm_fallback_to_local:
                raise
            logger.warning(
                "Cloud LLM call failed, falling back to local Ollama: %s",
                cloud_client.redact_secret(str(exc)),
            )
            result = ollama_generate_json(prompt, timeout=timeout, model=model, think=think, keep_alive=keep_alive)
            _last_call_metadata.set(
                CallMetadata(provider="ollama", model=model or settings.ollama_generate_model, fallback_used=True)
            )
            return result
        _last_call_metadata.set(
            CallMetadata(provider="cloud", model=settings.cloud_llm_model or "", fallback_used=False)
        )
        return result

    if chosen == "ollama":
        result = ollama_generate_json(prompt, timeout=timeout, model=model, think=think, keep_alive=keep_alive)
        _last_call_metadata.set(
            CallMetadata(provider="ollama", model=model or settings.ollama_generate_model, fallback_used=False)
        )
        return result

    raise ValueError(f"Unknown LLM provider: {chosen!r}")
