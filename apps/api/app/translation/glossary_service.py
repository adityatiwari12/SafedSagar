"""Version-controlled legal-terminology glossary (task Section 5).
Protects listed English terms from machine translation by swapping them
for opaque placeholder tokens before translate() and restoring the
original text afterwards - MT never sees, and so can never paraphrase or
mistranslate, a term like "prior art" or "Section 3(p)".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_GLOSSARY_PATH = Path(__file__).parent / "glossary" / "terms.yaml"

# Private-use-area character: never appears in real source text, safe as a
# placeholder delimiter that won't collide with translated output.
_TOKEN_TEMPLATE = "GLOSSARY{index}"


@dataclass(frozen=True)
class GlossaryTerm:
    english: str
    translations: dict[str, str]


class GlossaryService:
    def __init__(self, path: Path = _GLOSSARY_PATH):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        terms = [
            GlossaryTerm(english=t["en"], translations=t.get("translations") or {})
            for t in data.get("terms", [])
        ]
        # Longest-first so a multi-word term (e.g. "classical formulation")
        # matches before a shorter term that's also its substring.
        terms.sort(key=lambda t: len(t.english), reverse=True)
        self._terms = terms
        self._patterns = [
            (term, re.compile(rf"\b{re.escape(term.english)}\b", re.IGNORECASE)) for term in terms
        ]

    def protect(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace every glossary-term occurrence with a unique
        placeholder token. Returns the placeholdered text and a
        token -> original-substring map to pass to restore()."""
        placeholders: dict[str, str] = {}
        counter = 0
        result = text

        for _term, pattern in self._patterns:
            def _sub(match: re.Match) -> str:
                nonlocal counter
                token = _TOKEN_TEMPLATE.format(index=counter)
                counter += 1
                placeholders[token] = match.group(0)
                return token

            result = pattern.sub(_sub, result)

        return result, placeholders

    def restore(self, text: str, placeholders: dict[str, str]) -> str:
        for token, original in placeholders.items():
            text = text.replace(token, original)
        return text

    def localized_term(self, english_term: str, target_language: str) -> str | None:
        """A vetted localization, or None if unvetted - callers keep the
        English term rather than invent one (task Section 5)."""
        for term in self._terms:
            if term.english.lower() == english_term.lower():
                return term.translations.get(target_language)
        return None


@lru_cache(maxsize=1)
def get_glossary_service() -> GlossaryService:
    return GlossaryService()
