"""OpenAI-compatible chat completions client for optional cloud Llama."""

from __future__ import annotations

import json

import httpx

from app.config import settings


def generate_json(prompt: str, timeout: float = 120.0) -> dict:
    if not settings.cloud_llm_base_url or not settings.cloud_llm_model:
        raise RuntimeError(
            "CLOUD_LLM_BASE_URL and CLOUD_LLM_MODEL must be set when "
            "llm_provider=cloud"
        )
    base = settings.cloud_llm_base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if settings.cloud_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.cloud_llm_api_key}"
    resp = httpx.post(
        f"{base}/chat/completions",
        headers=headers,
        json={
            "model": settings.cloud_llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)
