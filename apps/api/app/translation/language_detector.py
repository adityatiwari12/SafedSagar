"""Language detection, independent of any translation provider.

Uses py3langid (pure-Python port of langid.py, no native/compiled deps -
installs cleanly on this venv's Python 3.14, unlike torch-based options).
Its language set already covers all 13 supported codes.
"""

from __future__ import annotations

import math

import py3langid as langid

from app.translation.languages import SUPPORTED_LANGUAGE_CODES

# py3langid's rank() scores are raw log-likelihoods, not probabilities.
# Softmax over the restricted candidate set turns them into a comparable
# [0, 1] confidence - a large margin between the top two candidates (the
# common case for a full sentence) collapses to ~1.0, while a short or
# code-mixed query that's genuinely ambiguous stays low, which is exactly
# when the caller should fall back to the user's selected UI language
# instead (task Section 2 - "If detection confidence is low...").
LOW_CONFIDENCE_THRESHOLD = 0.5

_restricted = False


def _ensure_restricted() -> None:
    global _restricted
    if not _restricted:
        langid.set_languages(list(SUPPORTED_LANGUAGE_CODES))
        _restricted = True


def detect_language(text: str) -> tuple[str, float]:
    """Return (language_code, confidence) restricted to the 13 supported
    languages. Confidence is a softmax-normalized score, not a calibrated
    probability - treat it as a ranking signal, not ground truth."""
    _ensure_restricted()
    stripped = text.strip()
    if not stripped:
        return "en", 0.0

    ranked = langid.rank(stripped)
    scores = [score for _, score in ranked]
    top_score = max(scores)
    exp_scores = [math.exp(score - top_score) for score in scores]
    total = sum(exp_scores)
    confidence = exp_scores[0] / total if total else 0.0

    top_language, _ = ranked[0]
    return top_language, confidence
