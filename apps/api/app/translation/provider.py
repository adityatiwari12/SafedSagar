"""The TranslationProvider abstraction (task Section 2/3) - keeps
IndicTrans2 (or a future Bhashini/other provider) behind one interface so
swapping the backend never touches the callers in chat/router.py or the
/translate endpoint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationResult:
    text: str
    source_language: str
    target_language: str
    provider: str


class TranslationUnavailableError(RuntimeError):
    """A provider could not service a translate() call - e.g. the
    IndicTrans2 sidecar process isn't running, or a language pair isn't
    supported. Callers must treat this as "translation unavailable", never
    silently pass through a garbled result."""


class TranslationProvider(ABC):
    name: str = "base"

    def detect(self, text: str) -> tuple[str, float]:
        """Default detection delegates to the shared, provider-independent
        language_detector. Override only if a provider ships its own
        higher-quality identifier (e.g. Bhashini's)."""
        from app.translation.language_detector import detect_language

        return detect_language(text)

    @abstractmethod
    def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult: ...

    @abstractmethod
    def supported_languages(self) -> list[str]: ...
