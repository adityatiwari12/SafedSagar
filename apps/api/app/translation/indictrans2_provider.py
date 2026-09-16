"""IndicTrans2 provider - calls a separate local sidecar process over
HTTP rather than importing torch/transformers in-process.

Why a sidecar: this API's venv is pinned to Python 3.14 (see
pyproject.toml's langgraph-exclusion note for the same class of problem)
and PyTorch ships no Windows wheel for plain cp314 as of this writing -
only the experimental free-threaded cp314t build, which nothing else here
targets. Python 3.12 (already installed on this machine) has full torch
support, so the sidecar runs there as its own process, called over HTTP -
the same pattern as the existing Ollama and ChromaDB integrations, not a
new architectural layer. See services/indictrans2-sidecar/README.md.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.translation.languages import SUPPORTED_LANGUAGE_CODES
from app.translation.provider import TranslationProvider, TranslationResult, TranslationUnavailableError


class IndicTrans2Provider(TranslationProvider):
    name = "indictrans2"

    # CPU-only NLLB-200/IndicTrans2 inference on this dev machine regularly
    # takes longer than 30s per call (verified live: sidecar logged a 200 OK
    # after the client had already given up and reported "unavailable") -
    # 90s gives real headroom without hanging a request forever.
    def __init__(self, base_url: str | None = None, timeout: float = 90.0):
        self._base_url = (base_url or settings.indictrans2_sidecar_url).rstrip("/")
        self._timeout = timeout

    def supported_languages(self) -> list[str]:
        return list(SUPPORTED_LANGUAGE_CODES)

    def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult:
        if source_language == target_language:
            return TranslationResult(
                text=text, source_language=source_language, target_language=target_language, provider=self.name
            )

        try:
            response = httpx.post(
                f"{self._base_url}/translate",
                json={
                    "text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TranslationUnavailableError(
                f"IndicTrans2 sidecar unreachable at {self._base_url}: {exc}"
            ) from exc

        data = response.json()
        return TranslationResult(
            text=data["text"],
            source_language=source_language,
            target_language=target_language,
            provider=self.name,
        )
