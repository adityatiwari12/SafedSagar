"""Facade for JSON generation — routes to Ollama (default) or cloud Llama."""

from __future__ import annotations

from app.config import settings
from app.llm import cloud_client, ollama_client

ollama_generate_json = ollama_client.generate_json
cloud_generate_json = cloud_client.generate_json


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
        return cloud_generate_json(prompt, timeout=timeout)
    if chosen == "ollama":
        return ollama_generate_json(prompt, timeout=timeout, model=model, think=think, keep_alive=keep_alive)
    raise ValueError(f"Unknown LLM provider: {chosen!r}")
