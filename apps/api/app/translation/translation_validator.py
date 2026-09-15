"""Mechanical, rule-based checks run AFTER translation (task Section 7).

Phase 1 catches the structural failure modes that would silently corrupt
a legal answer: a dropped/altered section-or-article reference, a mangled
URL, or a glossary placeholder that survived untranslated (meaning the MT
model choked on it rather than leaving it alone). It does NOT yet attempt
semantic checks - negation, modality (may/must/shall/should/cannot) -
since that needs an LLM-judge call; that's a follow-on phase, not a
silently-accepted gap (see docs/multilingual-architecture.md#validation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SECTION_REF_RE = re.compile(
    r"\b(?:Section|Rule|Article|Regulation)\s+\d+[A-Za-z]?(?:\(\w+\))*", re.IGNORECASE
)
_URL_RE = re.compile(r"https?://\S+")
_PLACEHOLDER_RE = re.compile(r"GLOSSARY\d+")


@dataclass(frozen=True)
class ValidationResult:
    status: str  # "verified" | "failed"
    issues: list[str] = field(default_factory=list)


class TranslationValidator:
    def validate(self, source_text: str, translated_text: str) -> ValidationResult:
        issues: list[str] = []

        source_sections = sorted(s.lower() for s in _SECTION_REF_RE.findall(source_text))
        translated_sections = sorted(s.lower() for s in _SECTION_REF_RE.findall(translated_text))
        if source_sections != translated_sections:
            issues.append(
                f"Section/rule/article references changed: {source_sections} -> {translated_sections}"
            )

        source_urls = sorted(_URL_RE.findall(source_text))
        translated_urls = sorted(_URL_RE.findall(translated_text))
        if source_urls != translated_urls:
            issues.append(f"URLs changed: {source_urls} -> {translated_urls}")

        leftover = _PLACEHOLDER_RE.findall(translated_text)
        if leftover:
            issues.append(f"Glossary placeholder(s) survived translation unresolved: {leftover}")

        return ValidationResult(status="failed" if issues else "verified", issues=issues)
