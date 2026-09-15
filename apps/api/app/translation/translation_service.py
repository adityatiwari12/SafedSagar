"""Facade the rest of the app talks to - hides which provider is active
and the protect/translate/restore/validate sequence behind two calls:
resolve_incoming (user language -> canonical English) and resolve_outgoing
(canonical English -> user language). Swapping IndicTrans2 for Bhashini
later means changing the provider passed in here, not any caller.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.translation.glossary_service import get_glossary_service
from app.translation.indictrans2_provider import IndicTrans2Provider
from app.translation.language_detector import LOW_CONFIDENCE_THRESHOLD, detect_language
from app.translation.languages import DEFAULT_LANGUAGE, is_supported
from app.translation.provider import TranslationProvider, TranslationUnavailableError
from app.translation.translation_validator import TranslationValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationOutcome:
    text: str
    source_language: str
    target_language: str
    translation_status: str  # "not_needed" | "verified" | "failed" | "unavailable"
    needs_human_review: bool


@dataclass(frozen=True)
class IncomingResolution:
    detected_language: str
    detection_confidence: float
    canonical_query: str
    translation_status: str
    needs_human_review: bool


class TranslationService:
    def __init__(self, provider: TranslationProvider | None = None):
        self._provider = provider or IndicTrans2Provider()
        self._glossary = get_glossary_service()
        self._validator = TranslationValidator()

    def translate_text(self, text: str, source_language: str, target_language: str) -> TranslationOutcome:
        if source_language == target_language or not text:
            return TranslationOutcome(
                text=text,
                source_language=source_language,
                target_language=target_language,
                translation_status="not_needed",
                needs_human_review=False,
            )

        protected_text, placeholders = self._glossary.protect(text)
        try:
            result = self._provider.translate(protected_text, source_language, target_language)
        except TranslationUnavailableError:
            logger.warning(
                "Translation provider unavailable for %s -> %s", source_language, target_language
            )
            return TranslationOutcome(
                text=text,
                source_language=source_language,
                target_language=target_language,
                translation_status="unavailable",
                needs_human_review=True,
            )

        translated = self._glossary.restore(result.text, placeholders)
        validation = self._validator.validate(text, translated)

        if validation.status == "failed":
            logger.warning(
                "Translation validation failed for %s -> %s: %s",
                source_language,
                target_language,
                validation.issues,
            )
            # Section 7: never silently return a potentially-incorrect legal
            # translation - fall back to the verified source text rather
            # than one that dropped/altered a citation, section number, or
            # URL.
            return TranslationOutcome(
                text=text,
                source_language=source_language,
                target_language=target_language,
                translation_status="failed",
                needs_human_review=True,
            )

        return TranslationOutcome(
            text=translated,
            source_language=source_language,
            target_language=target_language,
            translation_status="verified",
            needs_human_review=False,
        )

    def resolve_incoming(self, text: str, ui_language: str | None) -> IncomingResolution:
        detected, confidence = detect_language(text)
        if confidence < LOW_CONFIDENCE_THRESHOLD and is_supported(ui_language):
            detected = ui_language  # low-confidence detection: trust the UI's selected language

        outcome = self.translate_text(text, detected, DEFAULT_LANGUAGE)
        return IncomingResolution(
            detected_language=detected,
            detection_confidence=confidence,
            canonical_query=outcome.text,
            translation_status=outcome.translation_status,
            needs_human_review=outcome.needs_human_review,
        )

    def resolve_outgoing(self, canonical_answer: str, target_language: str) -> TranslationOutcome:
        return self.translate_text(canonical_answer, DEFAULT_LANGUAGE, target_language)


_service: TranslationService | None = None


def get_translation_service() -> TranslationService:
    global _service
    if _service is None:
        _service = TranslationService()
    return _service
