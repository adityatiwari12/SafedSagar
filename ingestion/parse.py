"""Extract plain text from a raw downloaded document (PDF, HTML, or MHT)."""

from __future__ import annotations

import email
import re
import shutil
import sys
from pathlib import Path

from pypdf import PdfReader

# Below this chars-per-page average, a PDF is likely scanned-image rather
# than text-layer - falls back to OCR (see _ocr_pdf) rather than being
# shipped through with near-empty chunks.
_SCANNED_HEURISTIC_CHARS_PER_PAGE = 200

# Per-page OCR is only worth it below this page count - a 500-page scanned
# gazette would take unreasonably long via tesseract; flag those instead
# of silently hanging the ingestion run.
_OCR_MAX_PAGES = 60

# Windows tesseract.exe installs here by default and is often not on PATH
# for a non-interactive shell even when it's on PATH for the user's normal
# terminal - checked as a fallback so pytesseract doesn't need the caller
# to have configured PATH first.
_WINDOWS_TESSERACT_FALLBACK = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def _configure_tesseract() -> None:
    import pytesseract

    if shutil.which("tesseract"):
        return
    if Path(_WINDOWS_TESSERACT_FALLBACK).exists():
        pytesseract.pytesseract.tesseract_cmd = _WINDOWS_TESSERACT_FALLBACK


def _ocr_pdf(raw_path: Path, reader: PdfReader) -> str:
    """OCR a scanned PDF by extracting each page's embedded scan image
    (pypdf, already a working dependency) and running tesseract.exe on it
    via pytesseract - deliberately NOT using a PDF-rasterizing library
    (e.g. PyMuPDF): its native DLL is blocked by this machine's Windows
    Application Control policy. pytesseract only shells out to the
    already-installed tesseract.exe, so it doesn't hit the same block.
    """
    import pytesseract

    page_count = len(reader.pages)
    if page_count > _OCR_MAX_PAGES:
        print(
            f"[warn] {raw_path.name}: {page_count} pages exceeds OCR cap "
            f"({_OCR_MAX_PAGES}) - skipping OCR, returning empty text. "
            f"Run OCR out-of-band for large scanned documents."
        )
        return ""

    _configure_tesseract()
    pages_text: list[str] = []
    for page_num, page in enumerate(reader.pages):
        page_images = list(page.images)
        if not page_images:
            print(f"[ocr]  {raw_path.name}: page {page_num + 1}/{page_count} -> no embedded image, skipped")
            continue
        # /Rotate is a page-display transform, not applied to the raw
        # embedded image pypdf hands back - a page.rotation of 90/180/270
        # means the scan itself is sideways/upside-down and needs the same
        # counter-rotation before OCR, or tesseract reads it sideways and
        # emits word-shaped garbage instead of erroring.
        rotation = page.rotation % 360
        # A scanned page is normally one full-page image; if a page has
        # several (e.g. a logo plus the body scan), OCR each and
        # concatenate rather than guessing which one is the "real" page.
        text = "\n".join(
            pytesseract.image_to_string(
                img.image.rotate(-rotation, expand=True) if rotation else img.image,
                lang="eng",
            )
            for img in page_images
        )
        pages_text.append(text)
        print(f"[ocr]  {raw_path.name}: page {page_num + 1}/{page_count} -> {len(text)} chars")
    return "\n\n".join(pages_text)


def parse_pdf(raw_path: Path) -> str:
    reader = PdfReader(str(raw_path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    total_chars = sum(len(t) for t in pages_text)
    avg_chars_per_page = total_chars / max(len(pages_text), 1)
    if avg_chars_per_page < _SCANNED_HEURISTIC_CHARS_PER_PAGE:
        print(
            f"[warn] {raw_path.name}: only {avg_chars_per_page:.0f} chars/page "
            f"across {len(pages_text)} pages - likely a scanned image PDF "
            f"with no usable text layer. Falling back to OCR."
        )
        return _ocr_pdf(raw_path, reader).replace("\x00", "")
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
