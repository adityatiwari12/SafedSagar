"""Language layer unit tests - no network, no DB (mirrors test_llm_generate.py's
pattern of mocking the one boundary that talks to a real process)."""

from app.translation.glossary_service import GlossaryService
from app.translation.language_detector import detect_language
from app.translation.provider import TranslationProvider, TranslationResult, TranslationUnavailableError
from app.translation.translation_service import TranslationService
from app.translation.translation_validator import TranslationValidator


def test_detect_language_english():
    lang, confidence = detect_language("Can I patent a classical Ayurvedic formulation?")
    assert lang == "en"
    assert confidence > 0.9


def test_detect_language_marathi():
    lang, confidence = detect_language("मी माझ्या आयुर्वेदिक फॉर्म्युलेशनचे पेटंट घेऊ शकतो का?")
    assert lang == "mr"
    assert confidence > 0.9


def test_detect_language_empty_string_is_low_confidence():
    lang, confidence = detect_language("   ")
    assert confidence == 0.0


def test_glossary_protects_and_restores_term():
    glossary = GlossaryService()
    protected, placeholders = glossary.protect("Prior art defeats this patent claim.")
    assert "prior art" not in protected.lower()
    assert "patent" not in protected.lower()
    restored = glossary.restore(protected, placeholders)
    assert restored == "Prior art defeats this patent claim."


def test_glossary_unvetted_term_has_no_localization():
    glossary = GlossaryService()
    assert glossary.localized_term("patent", "hi") is None


def test_validator_flags_changed_section_reference():
    validator = TranslationValidator()
    result = validator.validate(
        "This is governed by Section 3(p) of the Patents Act.",
        "This is governed by Section 3(k) of the Patents Act.",
    )
    assert result.status == "failed"
    assert any("Section" in issue for issue in result.issues)


def test_validator_flags_dropped_url():
    validator = TranslationValidator()
    result = validator.validate(
        "See https://ipindia.gov.in/act.pdf for details.",
        "See the act for details.",
    )
    assert result.status == "failed"


def test_validator_passes_when_structure_preserved():
    validator = TranslationValidator()
    result = validator.validate(
        "Section 3(p) of the Patents Act, 1970 applies.",
        "Section 3(p) of the Patents Act, 1970 applies (translated).",
    )
    assert result.status == "verified"


class _FakeProvider(TranslationProvider):
    name = "fake"

    def __init__(self, translated_text: str | None = None, unavailable: bool = False):
        self._translated_text = translated_text
        self._unavailable = unavailable

    def supported_languages(self) -> list[str]:
        return ["en", "hi"]

    def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult:
        if self._unavailable:
            raise TranslationUnavailableError("fake sidecar down")
        return TranslationResult(
            text=self._translated_text or text,
            source_language=source_language,
            target_language=target_language,
            provider=self.name,
        )


def test_translation_service_same_language_is_noop():
    service = TranslationService(provider=_FakeProvider())
    outcome = service.translate_text("hello", "en", "en")
    assert outcome.translation_status == "not_needed"
    assert outcome.text == "hello"


def test_translation_service_falls_back_when_provider_unavailable():
    service = TranslationService(provider=_FakeProvider(unavailable=True))
    outcome = service.translate_text("Section 3(p) applies.", "en", "hi")
    assert outcome.translation_status == "unavailable"
    assert outcome.needs_human_review is True
    assert outcome.text == "Section 3(p) applies."  # safe fallback: unmodified source


def test_translation_service_falls_back_when_validation_fails():
    # Fake provider "translates" by dropping the section reference entirely
    # - the validator must catch this and the service must refuse to
    # surface the corrupted result.
    service = TranslationService(provider=_FakeProvider(translated_text="This applies generally."))
    outcome = service.translate_text("Section 3(p) applies.", "en", "hi")
    assert outcome.translation_status == "failed"
    assert outcome.needs_human_review is True
    assert outcome.text == "Section 3(p) applies."


def test_translation_service_returns_translated_text_when_verified():
    service = TranslationService(provider=_FakeProvider(translated_text="Section 3(p) applies. [hi]"))
    outcome = service.translate_text("Section 3(p) applies.", "en", "hi")
    assert outcome.translation_status == "verified"
    assert outcome.needs_human_review is False
    assert outcome.text == "Section 3(p) applies. [hi]"


def test_resolve_incoming_low_confidence_falls_back_to_ui_language():
    service = TranslationService(provider=_FakeProvider())
    # A single ambiguous word is not enough for confident detection -
    # the UI-selected language should win per task Section 2.
    resolution = service.resolve_incoming("ok", "hi")
    assert resolution.detected_language == "hi"
