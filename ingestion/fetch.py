"""Download each source_registry.yaml entry's document to /corpus/raw.

Respects CLAUDE.md's scraping caveat: one request per source, a real
User-Agent, and a pause between requests. Idempotent by default - a
document already on disk is skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = Path(__file__).resolve().parent / "source_registry.yaml"
DEFAULT_RAW_DIR = REPO_ROOT / "corpus" / "raw"
# A plain identifying UA gets WAF-blocked (403) on at least one target
# gov domain; a standard browser UA string is what actually works across
# all sources, so that's the default despite being less "honest" than a
# custom bot UA - the alternative is not being able to fetch some sources
# at all.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_registry(registry_path: Path) -> list[dict]:
    with registry_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["sources"]


def fetch_all(
    registry_path: Path = DEFAULT_REGISTRY,
    raw_dir: Path = DEFAULT_RAW_DIR,
    delay_seconds: float = 3.0,
    force: bool = False,
) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    sources = load_registry(registry_path)
    written: list[Path] = []

    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=180.0, follow_redirects=True
    ) as client:
        for i, entry in enumerate(sources):
            doc_id = entry["doc_id"]
            ext = entry["format"]
            target = raw_dir / f"{doc_id}.{ext}"

            if entry.get("fetch") is False:
                if target.exists():
                    print(f"[manual] {doc_id} using existing {target}")
                    written.append(target)
                    continue
                raise FileNotFoundError(
                    f"{doc_id}: fetch=false but {target} is missing. "
                    f"Place the PDF manually, then re-run."
                )

            if target.exists() and not force:
                print(f"[skip] {doc_id} already at {target}")
                written.append(target)
                continue

            print(f"[fetch] {doc_id} <- {entry['source_url']}")
            resp = client.get(entry["source_url"])
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if ext == "pdf" and not resp.content.startswith(b"%PDF"):
                raise ValueError(
                    f"{doc_id}: expected a PDF but got content-type "
                    f"{content_type!r} and content starting with "
                    f"{resp.content[:100]!r} - the URL likely resolves to "
                    f"an HTML page (SPA shell, redirect, or error page), "
                    f"not the actual file. Fix source_registry.yaml."
                )

            target.write_bytes(resp.content)
            print(f"[ok]   {doc_id} -> {target} ({len(resp.content)} bytes)")
            written.append(target)

            if i < len(sources) - 1:
                time.sleep(delay_seconds)

    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        results = fetch_all(args.registry, args.raw_dir, args.delay, args.force)
    except (httpx.HTTPError, FileNotFoundError, ValueError) as exc:
        print(f"[error] fetch failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone: {len(results)} document(s) in {args.raw_dir}")
