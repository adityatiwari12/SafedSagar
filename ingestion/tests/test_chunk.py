"""Tests for ingestion.chunk, focused on the section-boundary detector.

Regression coverage for the year-as-section bug: _SECTION_MARKER_RE's
bare-number alternative ("<n>. ") matches any line starting with a number
and a period, including a four-digit year at a line start (a mis-wrapped
"Act, 1940" cross-reference or an amendment date like "2005. The rules
were amended..."). Unfiltered, that year became the section_or_article
label for the text that followed it - exactly the failure mode this
product cannot afford, since a wrong section number shown to a user reads
as a fabricated legal citation.
"""

from ingestion.chunk import _is_year_label, chunk_text

# Each synthetic "section body" needs to clear _MIN_STANDALONE_SECTION_CHARS
# (120) on its own, otherwise the merge-short-spans-forward logic would fold
# it into a neighbor and the test would be exercising that logic instead of
# the boundary detector.
_FILLER = "This is padding text describing the provision in some detail. " * 3


def _doc_with_year_line() -> str:
    return (
        "PREAMBLE. An Act to consolidate and amend certain provisions.\n\n"
        "1. Short title and commencement.\n"
        f"{_FILLER}\n\n"
        "2005. The rules were amended pursuant to a subsequent notification.\n"
        f"{_FILLER}\n\n"
        "3. Definitions.\n"
        f"{_FILLER}\n\n"
        "158B. Manufacture, sale and distribution of specified drugs.\n"
        f"{_FILLER}\n\n"
        "5. Miscellaneous provisions applicable to registered persons.\n"
        f"{_FILLER}\n\n"
        "6. Penalties for contravention of the foregoing provisions.\n"
        f"{_FILLER}\n"
    )


def test_year_at_line_start_is_not_a_section_boundary():
    chunks = chunk_text("test-doc", _doc_with_year_line())
    labels = [c["section_or_article"] for c in chunks]

    assert "2005" not in labels

    # The year line isn't dropped - it merges into the still-open section 1
    # span (the boundary before it is simply not recognized), so its text
    # must still be retrievable, just not under its own false label.
    joined = " ".join(c["source_text"] for c in chunks)
    assert "The rules were amended pursuant to a subsequent notification" in joined


def test_bare_low_section_number_still_creates_boundary():
    chunks = chunk_text("test-doc", _doc_with_year_line())
    labels = [c["section_or_article"] for c in chunks]
    assert "5" in labels


def test_real_high_section_number_still_creates_boundary():
    """158B is well outside the year-rejection range (1800-2099) and must
    be unaffected - Indian statutes commonly number amendment-inserted
    sections like "158B" that come after the original run of numbers."""
    chunks = chunk_text("test-doc", _doc_with_year_line())
    labels = [c["section_or_article"] for c in chunks]
    assert "158B" in labels

    chunk_158b = next(c for c in chunks if c["section_or_article"] == "158B")
    assert "Manufacture, sale and distribution of specified drugs" in chunk_158b["source_text"]


def test_year_line_merges_into_preceding_section_not_a_separate_or_lost_chunk():
    """Rejecting the year candidate should merely drop that boundary (so
    the text becomes part of the previous real section's span) rather than
    mislabeling it under some other section or silently dropping it."""
    chunks = chunk_text("test-doc", _doc_with_year_line())
    section_1 = next(c for c in chunks if c["section_or_article"] == "1")
    assert "The rules were amended pursuant to a subsequent notification" in section_1["source_text"]


def test_is_year_label_accepts_plain_four_digit_years_in_range():
    assert _is_year_label("1940") is True
    assert _is_year_label("2005") is True
    assert _is_year_label("1800") is True
    assert _is_year_label("2099") is True


def test_is_year_label_rejects_real_section_numbers():
    assert _is_year_label("5") is False
    assert _is_year_label("158B") is False
    assert _is_year_label("3A") is False
    # Just outside the assumed year range - still not a plausible section
    # number in this corpus, but out of scope for this filter; documents
    # the boundary rather than asserting a stronger claim.
    assert _is_year_label("2100") is False


def test_explicit_section_and_article_keyword_forms_also_reject_years():
    """The keyword-form alternatives ("Section N" / "Article N") get the
    same year filter as the bare-number form - a stray line starting
    "Section 1940." is just as implausible as a real section reference in
    this corpus as the bare-number case, so it isn't special-cased as
    exempt from the filter."""
    text = (
        "1. Short title.\n"
        f"{_FILLER}\n\n"
        "Section 1940 was a different Act entirely and is not in force.\n"
        f"{_FILLER}\n\n"
        "3. Definitions.\n"
        f"{_FILLER}\n\n"
        "Article 2005 of a foreign convention is out of scope here.\n"
        f"{_FILLER}\n\n"
        "5. Miscellaneous.\n"
        f"{_FILLER}\n\n"
        "6. Penalties.\n"
        f"{_FILLER}\n"
    )
    chunks = chunk_text("test-doc", text)
    labels = [c["section_or_article"] for c in chunks]
    assert "1940" not in labels
    assert "2005" not in labels
