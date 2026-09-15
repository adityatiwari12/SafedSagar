"""Split extracted document text into citable chunks.

Prefers splitting by detected statute section/article boundaries (so a
chunk maps to something an LLM can actually cite); falls back to
fixed-size sliding-window chunks when too few boundaries are found.
"""

from __future__ import annotations

import re

# Matches "3. ", "3A. ", "15AA. " etc. at the start of a line - the
# common Indian-statute numbering style - or explicit "Section N" /
# "Article N" labels.
_SECTION_MARKER_RE = re.compile(
    r"^\s*(?:(\d+[A-Z]{0,2})\.\s+|Section\s+(\d+[A-Z]{0,2})\b|Article\s+(\d+[A-Z]{0,2})\b)",
    re.MULTILINE,
)

_MIN_SECTION_MATCHES = 5
_MAX_SECTION_MULTIPLE = 3  # split a section further only past this x target_chars

# A statute's own "ARRANGEMENT OF SECTIONS" table of contents lists every
# section number as its own one-line entry ("1. Short title..."), which
# matches _SECTION_MARKER_RE just as well as a real section body does -
# left unhandled, each ToC line becomes its own near-empty "chunk" ahead
# of the real section text. A real section body is essentially always
# longer than this; a span shorter than it gets merged forward into
# whatever follows instead of standing alone.
_MIN_STANDALONE_SECTION_CHARS = 120

# Known limitation, deliberately not fixed here (CLAUDE.md caveat #3 - don't
# chase accuracy early): a ToC block spanning many short section-title
# lines can still merge into one chunk that gets labeled with whichever
# section number happens to cross the length threshold, so that label
# ends up attached to a "list of titles" chunk AND, separately, to the
# real section body appearing later in the document. Both chunks are
# real, retrievable text; the label is just imprecise on the ToC one.
# A real fix would detect and skip the "ARRANGEMENT OF SECTIONS" block
# structurally rather than by length heuristic.


def _sliding_window(full_text: str, target_chars: int, overlap_chars: int) -> list[dict]:
    chunks: list[dict] = []
    start = 0
    n = len(full_text)
    while start < n:
        end = min(start + target_chars, n)
        chunks.append({"section_or_article": None, "source_text": full_text[start:end].strip()})
        if end == n:
            break
        start = end - overlap_chars
    return [c for c in chunks if c["source_text"]]


def _split_oversized(label: str | None, text: str, target_chars: int, overlap_chars: int) -> list[dict]:
    if len(text) <= target_chars * _MAX_SECTION_MULTIPLE:
        return [{"section_or_article": label, "source_text": text.strip()}]
    sub_chunks = _sliding_window(text, target_chars, overlap_chars)
    for c in sub_chunks:
        c["section_or_article"] = label
    return sub_chunks


def chunk_text(
    doc_id: str,
    full_text: str,
    target_chars: int = 1500,
    overlap_chars: int = 200,
) -> list[dict]:
    matches = list(_SECTION_MARKER_RE.finditer(full_text))

    if len(matches) < _MIN_SECTION_MATCHES:
        return _sliding_window(full_text, target_chars, overlap_chars)

    raw_spans: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        label = next(g for g in m.groups() if g is not None)
        section_start = m.start()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        raw_spans.append((label, full_text[section_start:section_end]))

    merged_spans: list[tuple[str, str]] = []
    pending = ""
    for label, text in raw_spans:
        combined = pending + text
        if len(combined.strip()) >= _MIN_STANDALONE_SECTION_CHARS:
            merged_spans.append((label, combined))
            pending = ""
        else:
            pending = combined
    if pending.strip():
        # Trailing short span(s) with nothing after them to merge into -
        # attach to the last real chunk rather than dropping, or stand
        # alone if this document had no long spans at all.
        if merged_spans:
            last_label, last_text = merged_spans[-1]
            merged_spans[-1] = (last_label, last_text + pending)
        else:
            merged_spans.append((raw_spans[-1][0], pending))

    chunks: list[dict] = []
    for label, section_text in merged_spans:
        chunks.extend(_split_oversized(label, section_text, target_chars, overlap_chars))

    # Anything before the first detected section marker (preamble, title
    # block) becomes its own unlabeled leading chunk rather than being
    # silently dropped.
    if matches[0].start() > 0:
        preamble = full_text[: matches[0].start()].strip()
        if preamble:
            chunks.insert(0, {"section_or_article": None, "source_text": preamble})

    return chunks


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    import yaml

    def _safe_print(s: str) -> None:
        enc = sys.stdout.encoding or "utf-8"
        print(s.encode(enc, errors="replace").decode(enc, errors="replace"))

    from ingestion.parse import parse_document

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path(__file__).parent / "source_registry.yaml")
    parser.add_argument("--raw-dir", type=Path, default=Path(__file__).parent.parent / "corpus" / "raw")
    args = parser.parse_args()

    sources = yaml.safe_load(args.registry.read_text(encoding="utf-8"))["sources"]
    for entry in sources:
        raw_path = args.raw_dir / f"{entry['doc_id']}.{entry['format']}"
        text = parse_document(raw_path, entry["format"])
        chunks = chunk_text(entry["doc_id"], text)
        by_section = sum(1 for c in chunks if c["section_or_article"] is not None)
        mode = "section-based" if by_section else "fallback sliding-window"
        print(f"{entry['doc_id']}: {len(chunks)} chunks ({mode})")
        for c in chunks[:2]:
            preview = c["source_text"][:150].replace("\n", " ")
            _safe_print(f"  [{c['section_or_article']}] {preview!r}")
        print("---")
