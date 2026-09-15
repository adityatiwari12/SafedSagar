"""Extract plain text from a raw downloaded document (PDF, HTML, or MHT)."""

from __future__ import annotations

import email
import re
import sys
from pathlib import Path

from pypdf import PdfReader

# Below this chars-per-page average, a PDF is likely scanned-image rather
# than text-layer - flagged as a warning, not a hard failure (OCR is out
# of scope for this phase; a human should notice and decide what to do).
_SCANNED_HEURISTIC_CHARS_PER_PAGE = 200

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def parse_pdf(raw_path: Path) -> str:
    reader = PdfReader(str(raw_path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    total_chars = sum(len(t) for t in pages_text)
    avg_chars_per_page = total_chars / max(len(pages_text), 1)
    if avg_chars_per_page < _SCANNED_HEURISTIC_CHARS_PER_PAGE:
        print(
            f"[warn] {raw_path.name}: only {avg_chars_per_page:.0f} chars/page "
            f"across {len(pages_text)} pages - likely a scanned image PDF "
            f"with no usable text layer (OCR not implemented)."
        )
    return "\n\n".join(pages_text).replace("\x00", "")


def parse_html(raw_path: Path) -> str:
    raw = raw_path.read_text(encoding="utf-8", errors="replace")
    # Strip script/style blocks before stripping tags, so their content
    # doesn't leak into the extracted text.
    raw = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = _HTML_TAG_RE.sub(" ", raw)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def parse_mht(raw_path: Path) -> str:
    """MHT/MHTML - a browser-saved page (multipart/related MIME wrapping
    the HTML plus its embedded resources). Extract the text/html part and
    reuse the same tag-stripping as parse_html."""
    with raw_path.open("rb") as f:
        msg = email.message_from_bytes(f.read())

    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            html = payload.decode(charset, errors="replace")
            html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = _HTML_TAG_RE.sub(" ", html)
            text = _WHITESPACE_RE.sub(" ", text)
            text = _BLANK_LINES_RE.sub("\n\n", text)
            return text.strip()

    raise ValueError(f"{raw_path}: no text/html part found in MHT file")


def parse_document(raw_path: Path, doc_format: str) -> str:
    if doc_format == "pdf":
        return parse_pdf(raw_path)
    if doc_format == "html":
        return parse_html(raw_path)
    if doc_format == "mht":
        return parse_mht(raw_path)
    raise ValueError(f"unsupported format: {doc_format!r}")


if __name__ == "__main__":
    import argparse

    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path(__file__).parent / "source_registry.yaml")
    parser.add_argument("--raw-dir", type=Path, default=Path(__file__).parent.parent / "corpus" / "raw")
    args = parser.parse_args()

    sources = yaml.safe_load(args.registry.read_text(encoding="utf-8"))["sources"]
    for entry in sources:
        raw_path = args.raw_dir / f"{entry['doc_id']}.{entry['format']}"
        text = parse_document(raw_path, entry["format"])
        print(f"{entry['doc_id']}: {len(text)} chars extracted")
        preview = text[:300].replace("\n", " ")
        # Windows consoles default to cp1252, which can't encode every
        # character extracted from a PDF (e.g. bilingual gazette headers) -
        # degrade gracefully rather than crashing the demo print.
        print(preview.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))
        print("---")
