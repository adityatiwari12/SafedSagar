"""Language metadata for the 13 supported languages (PRD FR-12 / task
Section 2). A single source of truth for native/English names, script
direction, and the code list used to restrict language detection and
validate `language` fields elsewhere in the app.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    native_name: str
    english_name: str
    direction: str  # "ltr" | "rtl"
    script: str
    supported: bool = True


LANGUAGES: dict[str, LanguageInfo] = {
    "en": LanguageInfo("en", "English", "English", "ltr", "Latin"),
    "hi": LanguageInfo("hi", "हिन्दी", "Hindi", "ltr", "Devanagari"),
    "mr": LanguageInfo("mr", "मराठी", "Marathi", "ltr", "Devanagari"),
    "bn": LanguageInfo("bn", "বাংলা", "Bengali", "ltr", "Bengali"),
    "ta": LanguageInfo("ta", "தமிழ்", "Tamil", "ltr", "Tamil"),
    "te": LanguageInfo("te", "తెలుగు", "Telugu", "ltr", "Telugu"),
    "gu": LanguageInfo("gu", "ગુજરાતી", "Gujarati", "ltr", "Gujarati"),
    "kn": LanguageInfo("kn", "ಕನ್ನಡ", "Kannada", "ltr", "Kannada"),
    "ml": LanguageInfo("ml", "മലയാളം", "Malayalam", "ltr", "Malayalam"),
    "pa": LanguageInfo("pa", "ਪੰਜਾਬੀ", "Punjabi", "ltr", "Gurmukhi"),
    "or": LanguageInfo("or", "ଓଡ଼ିଆ", "Odia", "ltr", "Odia"),
    "as": LanguageInfo("as", "অসমীয়া", "Assamese", "ltr", "Bengali"),
    "ur": LanguageInfo("ur", "اردو", "Urdu", "rtl", "Arabic"),
}

SUPPORTED_LANGUAGE_CODES: tuple[str, ...] = tuple(LANGUAGES.keys())

# Canonical pivot language: everything is translated to/from English before
# touching the existing RAG pipeline (task Section 4 - "do NOT create
# separate knowledge bases per language").
DEFAULT_LANGUAGE = "en"


def is_supported(code: str | None) -> bool:
    return bool(code) and code in LANGUAGES


def get_language(code: str) -> LanguageInfo:
    return LANGUAGES[code]
