"""Probe candidate source URLs; require real PDFs (%PDF magic), not SPA HTML."""

from __future__ import annotations

import argparse
import sys
import time

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Verified PASS URLs as of 2026-09-15 (Wave A). Re-run before registry edits.
CANDIDATES: list[tuple[str, str]] = [
    ("trips", "https://www.wto.org/english/docs_e/legal_e/27-trips.pdf"),
    ("cbd", "https://www.cbd.int/doc/legal/cbd-en.pdf"),
    ("pct", "https://www.wipo.int/documents/d/pct-system/docs-en-texts-pct.pdf"),
    ("paris", "https://www.wipo.int/edocs/pubdocs/en/wipo_pub_201.pdf"),
    ("budapest", "https://www.wipo.int/edocs/pubdocs/en/wipo_pub_277.pdf"),
    (
        "gratk",
        "https://www.wipo.int/edocs/mdocs/tk/en/gratk_dc/gratk_dc_7.pdf",
    ),
    (
        "tm-act",
        "https://ipindia.gov.in/frontend/pdf/trade-mark/act/1_43_1_trade-marks-act.pdf",
    ),
    (
        "designs-act",
        "https://ipindia.gov.in/storage/uploads/docs-operator/b86a073f-f3f5-4484-b98c-1ca21cd846a3.pdf",
    ),
    (
        "patents-rules",
        "https://ipindia.gov.in/frontend/pdf/patents/rules/Indian_Patent_Rules_2003__1_.pdf",
    ),
    ("gi-act", "https://faolex.fao.org/docs/pdf/ind82321.pdf"),
    ("gi-rules", "https://faolex.fao.org/docs/pdf/ind183134.pdf"),
    (
        "copyright",
        "https://web.archive.org/web/20240101120000/https://copyright.gov.in/documents/copyrightrules1957.pdf",
    ),
    (
        "drugs-cosmetics",
        "https://cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/acts_rules/2016DrugsandCosmeticsAct1940Rules1945.pdf",
    ),
    (
        "bd-amend-2023",
        "https://web.archive.org/web/20240801000000/https://egazette.gov.in/WriteReadData/2023/247815.pdf",
    ),
    (
        "divya-pharmacy",
        "https://cdnbbsr.s3waas.gov.in/s3fcdb3b4550e745d29a64a696047067b7/uploads/2025/02/20250225762744805.pdf",
    ),
]


def probe(url: str, client: httpx.Client) -> tuple[bool, str]:
    resp = client.get(url)
    ct = resp.headers.get("content-type", "")
    size = len(resp.content)
    is_pdf = resp.content.startswith(b"%PDF") and size > 10_000
    detail = f"status={resp.status_code} ct={ct!r} size={size} pdf={is_pdf}"
    return is_pdf and resp.status_code == 200, detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--url", action="append", default=[], help="Extra URL to probe")
    parser.add_argument(
        "--hint",
        action="append",
        default=[],
        help="Hint label for a --url (same order); defaults to extra-N",
    )
    args = parser.parse_args()

    extras: list[tuple[str, str]] = []
    for i, u in enumerate(args.url):
        hint = args.hint[i] if i < len(args.hint) else f"extra-{i}"
        extras.append((hint, u))
    rows = CANDIDATES + extras
    failed = 0

    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=90.0, follow_redirects=True
    ) as client:
        for i, (hint, url) in enumerate(rows):
            try:
                ok, detail = probe(url, client)
            except httpx.HTTPError as exc:
                ok, detail = False, f"error={exc}"
            mark = "PASS" if ok else "FAIL"
            if not ok:
                failed += 1
            print(f"[{mark}] {hint}: {detail}\n  {url}")
            if i < len(rows) - 1:
                time.sleep(args.delay)

    print(f"\n{len(rows) - failed}/{len(rows)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
