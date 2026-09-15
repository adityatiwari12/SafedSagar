# Corpus Expansion + Faster Hybrid RAG + Llama Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Wave A legal corpus (India IP/ABS/drugs + key treaties + Divya Pharmacy), speed up hybrid retrieval (BM25 cache + parallel legs), and make Llama effective via tighter cite prompts plus an optional OpenAI-compatible cloud provider — without fine-tuning.

**Architecture:** Reuse the Phase 2 ingestion chain driven by `source_registry.yaml`. Verify every URL with the existing `%PDF` gate before registry commit. Speed up `retrieve` with a process-level BM25 cache and `asyncio.gather`. Route generation through a thin `generate_json` facade (`ollama` default | `cloud` optional). Keep `validate_citations` as the anti-hallucination gate. No LoRA.

**Tech Stack:** Python, httpx, pypdf, rank_bm25, ChromaDB, Postgres/SQLAlchemy, Ollama (`nomic-embed-text` + `llama3.2`), optional OpenAI-compatible cloud Llama, pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-corpus-expand-and-faster-rag-design.md`

## Global Constraints

- Rate-limited fetches (~3s between requests); browser-like User-Agent (existing `fetch.py`).
- Every registered PDF URL must return a body starting with `%PDF` (not SPA `text/html`).
- Mirror order when official fails: IPO/India Code static → FAOLEX → Wayback; document in `notes`.
- GRATK is signed, **not yet in force** — never present as binding law.
- TKDL is not scrapable — pointer only; out of Wave A content.
- No Indian Kanoon HTML scrape; Divya Pharmacy is hand-curated PDF only.
- Embeddings stay `nomic-embed-text` (no mid-corpus swap).
- No fine-tuning in this wave.
- Raw PDFs stay gitignored; commit registry + code + docs only.
- `SourceDocument` has no `updated_at` — BM25 cache invalidation uses row-count probe + explicit `invalidate_bm25_cache()`.

## File structure (locked)

| Path | Responsibility |
|---|---|
| `ingestion/verify_urls.py` | CLI: probe candidate URLs; print PASS/FAIL + content-type + size |
| `ingestion/source_registry.yaml` | Authoritative Wave A source list (verified URLs only) |
| `ingestion/fetch.py` | Download (honor `fetch: false` for hand-placed PDFs) |
| `ingestion/parse.py` / `chunk.py` / `embed_and_load.py` | Unchanged pipeline; re-run after registry expands |
| `apps/api/app/graph/nodes/retrieve.py` | BM25 cache + parallel vector/BM25 |
| `apps/api/app/graph/nodes/reason_and_cite.py` | Jurisdiction lock + GRATK + abstain prompts |
| `apps/api/app/llm/ollama_client.py` | Keep embed + ollama generate |
| `apps/api/app/llm/cloud_client.py` | OpenAI-compatible JSON generate |
| `apps/api/app/llm/generate.py` | Facade: `generate_json(prompt, *, provider=None)` |
| `apps/api/app/config.py` + `.env.example` | `LLM_PROVIDER`, cloud settings |
| `apps/api/tests/test_retrieve_cache.py` | BM25 cache + invalidate |
| `apps/api/tests/test_llm_generate.py` | Facade routing (mocked httpx) |
| `apps/api/tests/test_reason_and_cite_prompt.py` | Prompt contains jurisdiction/GRATK rules (unit, no LLM) |

---

### Task 1: URL verification helper + Wave A candidate probe

**Files:**
- Create: `ingestion/verify_urls.py`
- Test: manual CLI run (no pytest required for this task)

**Interfaces:**
- Consumes: nothing from later tasks
- Produces: CLI that prints verification results; human uses output to write Task 2 registry

- [ ] **Step 1: Write `ingestion/verify_urls.py`**

```python
"""Probe candidate source URLs; require real PDFs (%%PDF magic), not SPA HTML."""

from __future__ import annotations

import argparse
import sys
import time

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Starter candidates — replace/extend during the run; only PASS URLs enter the registry.
CANDIDATES: list[tuple[str, str]] = [
    # (doc_id_hint, url)
    ("trips", "https://www.wto.org/english/docs_e/legal_e/27-trips.pdf"),
    ("cbd", "https://www.cbd.int/doc/legal/cbd-en.pdf"),
    ("paris", "https://www.wipo.int/wipolex/en/text/287556"),  # often HTML — expect FAIL; find PDF mirror
    ("pct", "https://www.wipo.int/export/sites/www/pct/en/texts/pdf/pct.pdf"),
    ("budapest", "https://www.wipo.int/export/sites/www/treaties/en/documents/pdf/budapest.pdf"),
    # India — prefer FAOLEX / ipindia static PDFs; India Code SPA usually FAILs
    ("tm-act", "https://faolex.fao.org/docs/pdf/ind39905.pdf"),  # verify live
    ("designs-act", "https://faolex.fao.org/docs/pdf/ind39906.pdf"),  # verify live
    ("gi-act", "https://faolex.fao.org/docs/pdf/ind39907.pdf"),  # verify live
    ("copyright-act", "https://faolex.fao.org/docs/pdf/ind39908.pdf"),  # verify live — replace if wrong
    ("ppvfr", "https://faolex.fao.org/docs/pdf/ind37272.pdf"),  # verify live
    ("drugs-cosmetics", "https://faolex.fao.org/docs/pdf/ind18307.pdf"),  # verify live
    ("magic-remedies", "https://faolex.fao.org/docs/pdf/ind18308.pdf"),  # verify live
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
    args = parser.parse_args()

    extras = [("extra", u) for u in args.url]
    rows = CANDIDATES + extras
    failed = 0

    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True
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
```

**Important:** FAOLEX IDs above are **guesses for the plan scaffold**. The executor MUST treat FAIL as normal, search for real stable PDFs (FAOLEX search, ipindia.gov.in `/frontend/pdf/...`, Wayback), and only keep PASS URLs. Wrong IDs must not be copied into the registry.

- [ ] **Step 2: Run the probe**

Run (from repo root, ingestion venv or api venv with httpx):

```bash
python -m ingestion.verify_urls
```

Expected: mix of PASS/FAIL. Record every PASS URL for Task 2. For each FAIL, try alternate mirrors with `--url` until PASS or drop that doc from Wave A with a note in the registry commit message / task log.

Also probe (add via `--url` as discovered):

- Patents Rules 2024 / amended Patents Rules PDF from ipindia
- BD Amendment Act 2023 / BD Rules 2024
- GRATK official PDF (WIPO)
- Divya Pharmacy judgment PDF if a stable public URL exists

- [ ] **Step 3: Commit the helper only (not failed guesses as registry entries)**

```bash
git add ingestion/verify_urls.py
git commit -m "chore(ingestion): add PDF URL verification helper for Wave A corpus"
```

---

### Task 2: Expand `source_registry.yaml` with verified Wave A entries

**Files:**
- Modify: `ingestion/source_registry.yaml`
- Modify: `ingestion/fetch.py` (add `fetch: false` support)

**Interfaces:**
- Consumes: PASS URLs from Task 1
- Produces: registry entries ready for `fetch.py`; `fetch_all` skips hand-placed docs

- [ ] **Step 1: Extend `fetch.py` to honor `fetch: false`**

In the loop inside `fetch_all`, after resolving `target`:

```python
            if entry.get("fetch") is False:
                if target.exists():
                    print(f"[manual] {doc_id} using existing {target}")
                    written.append(target)
                    continue
                raise FileNotFoundError(
                    f"{doc_id}: fetch=false but {target} is missing. "
                    f"Place the PDF manually, then re-run."
                )
```

Keep the existing `%PDF` check for downloaded files.

- [ ] **Step 2: Append only verified entries to `source_registry.yaml`**

Keep the existing four sources. For each Wave A doc that passed verification, add a block matching the existing shape, for example:

```yaml
  - doc_id: wto-trips-1994
    title: "Agreement on Trade-Related Aspects of Intellectual Property Rights (TRIPS)"
    authority: "World Trade Organization"
    jurisdiction: international
    doc_type: treaty
    source_url: "https://www.wto.org/english/docs_e/legal_e/27-trips.pdf"
    format: pdf
    version: "1994"
    effective_date: "1995-01-01"
    last_verified_date: "2026-09-15"

  - doc_id: cbd-1992
    title: "Convention on Biological Diversity"
    authority: "Secretariat of the Convention on Biological Diversity"
    jurisdiction: international
    doc_type: treaty
    source_url: "https://www.cbd.int/doc/legal/cbd-en.pdf"
    format: pdf
    version: "1992"
    effective_date: "1993-12-29"
    last_verified_date: "2026-09-15"
```

Repeat for every PASS India statute/rules and remaining treaties. For GRATK:

```yaml
    notes: "WIPO Treaty on Intellectual Property, Genetic Resources and Associated Traditional Knowledge (adopted 24 May 2024). Signed but NOT YET IN FORCE — needs further ratifications. Present as signed/not binding, never as active law."
```

For Divya Pharmacy if only a local file is available:

```yaml
  - doc_id: divya-pharmacy-v-uoi
    title: "Divya Pharmacy v. Union of India (Uttarakhand High Court)"
    authority: "High Court of Uttarakhand"
    jurisdiction: india
    doc_type: case_law
    source_url: "https://example.invalid/replace-with-provenance-url-or-judgment-citation"
    format: pdf
    version: "judgment"
    effective_date: null
    last_verified_date: "2026-09-15"
    fetch: false
    notes: "Hand-curated judgment PDF placed at corpus/raw/divya-pharmacy-v-uoi.pdf. Not auto-fetched. Replace source_url with real provenance citation."
```

If a target Act cannot be verified as PDF in this session, **omit it** from the registry and list the omission in the commit message rather than shipping a broken URL.

- [ ] **Step 3: Smoke-fetch**

```bash
python -m ingestion.fetch
```

Expected: each auto entry downloads to `corpus/raw/{doc_id}.pdf` starting with `%PDF`; manual entry requires file present or clear `FileNotFoundError`.

- [ ] **Step 4: Commit**

```bash
git add ingestion/source_registry.yaml ingestion/fetch.py
git commit -m "feat(ingestion): register verified Wave A IP/ABS/treaty corpus sources"
```

---

### Task 3: Parse → chunk → embed Wave A

**Files:**
- Touch: `corpus/processed/*.json` (generated, may be gitignored — do not commit raw PDFs)
- Run: existing `ingestion/parse.py`, `chunk.py`, `embed_and_load.py`

**Interfaces:**
- Consumes: `corpus/raw/*.pdf` from Task 2
- Produces: Postgres `source_documents` rows + Chroma `source_chunks` vectors for all Wave A `doc_id`s

- [ ] **Step 1: Parse all raw PDFs**

```bash
python -m ingestion.parse
```

Expected: one processed artifact per `doc_id` without empty text.

- [ ] **Step 2: Chunk**

```bash
python -m ingestion.chunk
```

Expected: section-aware chunks where headings exist; fallback chunks otherwise.

- [ ] **Step 3: Embed and load**

Requires: Ollama running with `nomic-embed-text`, Postgres + Chroma up (`infra/docker-compose`).

```bash
python -m ingestion.embed_and_load
```

Expected: rows in `source_documents` for new `doc_id`s; Chroma collection queryable.

- [ ] **Step 4: Spot-check SQL**

```bash
# from apps/api venv / psql
psql "$DATABASE_URL" -c "SELECT doc_id, count(*) FROM source_documents GROUP BY doc_id ORDER BY doc_id;"
```

Expected: counts for old four + every newly ingested `doc_id`.

- [ ] **Step 5: Commit only code/docs if any small fixes were needed**

If parse/chunk needed a bugfix for a new PDF, commit that fix. Do **not** commit `corpus/raw/`.

```bash
git status
# git add only intentional code fixes, then:
git commit -m "fix(ingestion): handle Wave A PDF edge cases during parse/chunk"
```

If no code changes, skip commit.

---

### Task 4: Faster retrieval — BM25 cache + parallel hybrid

**Files:**
- Modify: `apps/api/app/graph/nodes/retrieve.py`
- Create: `apps/api/tests/test_retrieve_cache.py`

**Interfaces:**
- Consumes: `SourceDocument` rows; `embed(texts) -> list[list[float]]`
- Produces:
  - `invalidate_bm25_cache() -> None`
  - `retrieve(state) -> {vector_candidates, bm25_candidates}` with cached BM25 + parallel legs

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_retrieve_cache.py`:

```python
"""BM25 cache behaviour — pure unit tests with stubs (no Postgres/Chroma)."""

from __future__ import annotations

import apps.api.app.graph.nodes.retrieve as retrieve_mod


class _FakeRow:
    def __init__(self, id_: str, text: str):
        self.id = id_
        self.doc_id = "doc"
        self.section_or_article = "1"
        self.source_text = text
        self.title = "t"
        self.source_url = "u"


def test_invalidate_bm25_cache_clears_module_cache():
    retrieve_mod._bm25_cache["india|None"] = object()
    retrieve_mod.invalidate_bm25_cache()
    assert retrieve_mod._bm25_cache == {}


def test_cache_key_includes_jurisdiction_and_doc_type():
    assert retrieve_mod._bm25_cache_key("india", "statute") == "india|statute"
    assert retrieve_mod._bm25_cache_key(None, None) == "None|None"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
cd apps/api && pytest tests/test_retrieve_cache.py -v
```

Expected: FAIL (missing `invalidate_bm25_cache` / `_bm25_cache_key` / `_bm25_cache`).

- [ ] **Step 3: Implement cache + parallel gather in `retrieve.py`**

Replace the BM25 rebuild path and sequential calls with:

```python
import asyncio
from dataclasses import dataclass

_bm25_cache: dict[str, "_Bm25Entry"] = {}


@dataclass
class _Bm25Entry:
    row_count: int
    rows: list  # SourceDocument-like
    tokenized: list[list[str]]
    bm25: BM25Okapi


def _bm25_cache_key(jurisdiction: str | None, doc_type: str | None) -> str:
    return f"{jurisdiction}|{doc_type}"


def invalidate_bm25_cache() -> None:
    _bm25_cache.clear()


async def _filtered_rows(jurisdiction: str | None, doc_type: str | None) -> list:
    async with AsyncSessionLocal() as session:
        stmt = select(SourceDocument)
        if jurisdiction:
            stmt = stmt.where(SourceDocument.jurisdiction == jurisdiction)
        if doc_type:
            stmt = stmt.where(SourceDocument.doc_type == doc_type)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _get_bm25_entry(jurisdiction: str | None, doc_type: str | None) -> _Bm25Entry | None:
    key = _bm25_cache_key(jurisdiction, doc_type)
    rows = await _filtered_rows(jurisdiction, doc_type)
    if not rows:
        _bm25_cache.pop(key, None)
        return None

    cached = _bm25_cache.get(key)
    if cached is not None and cached.row_count == len(rows):
        return cached

    tokenized = [_tokenize(row.source_text) for row in rows]
    entry = _Bm25Entry(
        row_count=len(rows),
        rows=rows,
        tokenized=tokenized,
        bm25=BM25Okapi(tokenized),
    )
    _bm25_cache[key] = entry
    return entry


async def _bm25_search(question: str, jurisdiction: str | None, doc_type: str | None) -> list[RetrievedChunk]:
    entry = await _get_bm25_entry(jurisdiction, doc_type)
    if entry is None:
        return []
    scores = entry.bm25.get_scores(_tokenize(question))
    ranked = sorted(zip(entry.rows, scores), key=lambda pair: pair[1], reverse=True)
    return [_row_to_chunk(row) for row, score in ranked[:BM25_TOP_N] if score > 0]


async def retrieve(state: GraphState) -> dict:
    question = state["question"]
    jurisdiction = state.get("jurisdiction")
    doc_type = state.get("doc_type")

    vector_candidates, bm25_candidates = await asyncio.gather(
        _vector_search(question, jurisdiction, doc_type),
        _bm25_search(question, jurisdiction, doc_type),
    )
    return {
        "vector_candidates": vector_candidates,
        "bm25_candidates": bm25_candidates,
    }
```

Optional hardening (include if easy): wrap the sync `embed([...])` call inside `_vector_search` with `await asyncio.to_thread(embed, [question])` so the two legs can overlap on the event loop. Keep behavior identical.

Call `invalidate_bm25_cache()` at the end of `ingestion/embed_and_load.py` main success path via a best-effort import (or document that API process restart clears cache — prefer explicit invalidate if import path is clean; otherwise document restart-after-ingest in the commit message).

- [ ] **Step 4: Re-run tests — expect pass**

```bash
cd apps/api && pytest tests/test_retrieve_cache.py tests/test_graph_nodes.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/graph/nodes/retrieve.py apps/api/tests/test_retrieve_cache.py ingestion/embed_and_load.py
git commit -m "perf(retrieve): cache BM25 indexes and run hybrid search in parallel"
```

---

### Task 5: Llama facade (ollama default + optional cloud) + prompt tightening

**Files:**
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/.env.example`
- Create: `apps/api/app/llm/cloud_client.py`
- Create: `apps/api/app/llm/generate.py`
- Modify: `apps/api/app/graph/nodes/reason_and_cite.py`
- Modify: `apps/api/app/graph/nodes/classify_product.py` (import path only)
- Modify: `apps/api/app/graph/nodes/route_jurisdiction.py` (import path only)
- Modify: `apps/api/app/graph/nodes/route_ip_type.py` (import path only)
- Create: `apps/api/tests/test_llm_generate.py`
- Create: `apps/api/tests/test_reason_and_cite_prompt.py`

**Interfaces:**
- Consumes: `Settings` provider fields
- Produces:
  - `generate_json(prompt: str, timeout: float = 120.0, *, provider: str | None = None) -> dict`
  - Cloud path: POST `{CLOUD_LLM_BASE_URL}/v1/chat/completions` with `response_format: {type: json_object}`

- [ ] **Step 1: Write failing facade tests**

`apps/api/tests/test_llm_generate.py`:

```python
from unittest.mock import MagicMock, patch

from app.llm import generate as generate_mod


def test_generate_json_routes_to_ollama_by_default(monkeypatch):
    monkeypatch.setattr(generate_mod.settings, "llm_provider", "ollama")
    with patch("app.llm.generate.ollama_generate_json", return_value={"ok": True}) as m:
        assert generate_mod.generate_json("hi") == {"ok": True}
        m.assert_called_once()


def test_generate_json_routes_to_cloud(monkeypatch):
    monkeypatch.setattr(generate_mod.settings, "llm_provider", "cloud")
    with patch("app.llm.generate.cloud_generate_json", return_value={"ok": True}) as m:
        assert generate_mod.generate_json("hi") == {"ok": True}
        m.assert_called_once()


def test_provider_override_wins(monkeypatch):
    monkeypatch.setattr(generate_mod.settings, "llm_provider", "ollama")
    with patch("app.llm.generate.cloud_generate_json", return_value={"c": 1}) as m:
        assert generate_mod.generate_json("hi", provider="cloud") == {"c": 1}
        m.assert_called_once()
```

`apps/api/tests/test_reason_and_cite_prompt.py`:

```python
from app.graph.nodes import reason_and_cite as rac


def test_prompt_template_locks_jurisdiction_and_gratk():
    text = rac._PROMPT_TEMPLATE
    assert "jurisdiction" in text.lower() or "JURISDICTION" in text
    assert "not legal advice" in text.lower()
    assert "NOT YET" in text or "not yet" in text.lower() or "GRATK" in text
```

Adjust assertions to match the exact prompt wording you write in Step 3.

- [ ] **Step 2: Run tests — expect fail**

```bash
cd apps/api && pytest tests/test_llm_generate.py tests/test_reason_and_cite_prompt.py -v
```

Expected: FAIL (module/settings missing).

- [ ] **Step 3: Extend `Settings` and `.env.example`**

In `config.py` add:

```python
    llm_provider: str = "ollama"  # ollama | cloud
    llm_reasoning_provider: str | None = None
    cloud_llm_base_url: str | None = None
    cloud_llm_api_key: str | None = None
    cloud_llm_model: str | None = None
```

Keep existing `ollama_*` fields. Append matching keys to `.env.example` (no secrets).

- [ ] **Step 4: Implement `cloud_client.py` and `generate.py`**

`cloud_client.py`:

```python
"""OpenAI-compatible chat completions client for optional cloud Llama."""

from __future__ import annotations

import json

import httpx

from app.config import settings


def generate_json(prompt: str, timeout: float = 120.0) -> dict:
    if not settings.cloud_llm_base_url or not settings.cloud_llm_model:
        raise RuntimeError("CLOUD_LLM_BASE_URL and CLOUD_LLM_MODEL must be set for llm_provider=cloud")
    base = settings.cloud_llm_base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if settings.cloud_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.cloud_llm_api_key}"
    resp = httpx.post(
        f"{base}/chat/completions",
        headers=headers,
        json={
            "model": settings.cloud_llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)
```

`generate.py`:

```python
from __future__ import annotations

from app.config import settings
from app.llm import cloud_client, ollama_client

ollama_generate_json = ollama_client.generate_json
cloud_generate_json = cloud_client.generate_json


def generate_json(prompt: str, timeout: float = 120.0, *, provider: str | None = None) -> dict:
    chosen = (provider or settings.llm_provider or "ollama").lower()
    if chosen == "cloud":
        return cloud_generate_json(prompt, timeout=timeout)
    if chosen == "ollama":
        return ollama_generate_json(prompt, timeout=timeout)
    raise ValueError(f"Unknown LLM provider: {chosen!r}")
```

- [ ] **Step 5: Point graph nodes at the facade; tighten `reason_and_cite` prompt**

Change imports in classify/route/reason nodes from `app.llm.ollama_client import generate_json` to `app.llm.generate import generate_json`.

In `reason_and_cite`, if `settings.llm_reasoning_provider` is set, call `generate_json(prompt, provider=settings.llm_reasoning_provider)`.

Update `_PROMPT_TEMPLATE` to include (exact text may vary; tests must match):

```text
JURISDICTION FOR THIS ANSWER: {jurisdiction}
Use ONLY the numbered source chunks below. Do not cite or invent authority
from any other jurisdiction. If the chunks are insufficient, abstain plainly.

If any chunk is from the WIPO GRATK treaty, you MUST state it is signed but
NOT YET IN FORCE / not binding law.
```

Pass `jurisdiction=state.get("jurisdiction") or "unspecified"` into the format call. Retrieve already filters by jurisdiction; the prompt reinforces the lock.

- [ ] **Step 6: Run tests — expect pass**

```bash
cd apps/api && pytest tests/test_llm_generate.py tests/test_reason_and_cite_prompt.py tests/test_graph_nodes.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/config.py apps/api/.env.example apps/api/app/llm/cloud_client.py apps/api/app/llm/generate.py apps/api/app/graph/nodes/*.py apps/api/tests/test_llm_generate.py apps/api/tests/test_reason_and_cite_prompt.py
git commit -m "feat(llm): optional cloud Llama provider and stricter cite prompts"
```

---

### Task 6: End-to-end smoke (corpus + retrieve + cite)

**Files:**
- None required (manual smoke); optional: `docs/superpowers/plans/` checklist update

**Interfaces:**
- Consumes: ingested Wave A corpus + running API stack
- Produces: recorded smoke results (pass/fail notes in commit message or short `docs/` note only if useful)

- [ ] **Step 1: Confirm services**

Ollama up; `docker compose` Postgres + Chroma up; API can import settings.

- [ ] **Step 2: Three smoke questions** (via existing chat/graph entrypoint or a small `python -c` invoking the graph)

1. India patent: classical Ayurvedic formulation / Section 3(p) style question → expect Patents Act citations, `jurisdiction=india`
2. India ABS: biological resource access → expect BD Act / Divya Pharmacy if ingested
3. International: TRIPS / CBD question with jurisdiction international → expect treaty citations, no India statute blend

- [ ] **Step 3: Confirm**

- `validated_citations` non-empty when chunks support the answer
- GRATK (if asked) marked not in force
- Second identical query is not slower due to BM25 rebuild (informal timing OK)

- [ ] **Step 4: Commit design + plan docs if not already committed**

```bash
git add docs/superpowers/specs/2026-09-15-corpus-expand-and-faster-rag-design.md docs/superpowers/plans/2026-09-15-corpus-expand-and-faster-rag.md
git commit -m "docs: Wave A corpus expansion and faster RAG design + plan"
```

---

## Spec coverage self-review

| Spec requirement | Task |
|---|---|
| Wave A India IP/drugs/ABS docs | Tasks 1–3 |
| International treaties + GRATK caveat | Tasks 1–2, 5 |
| Divya Pharmacy hand-curated | Task 2 (`fetch: false`) |
| `%PDF` verification / mirrors | Tasks 1–2 |
| BM25 cache + parallel hybrid | Task 4 |
| Optional cloud Llama + local default | Task 5 |
| Prompt jurisdiction lock / abstain | Task 5 |
| No fine-tuning | Global constraint; no task adds LoRA |
| Embeddings unchanged | Global constraint |
| Smoke success criteria | Task 6 |

## Placeholder / consistency self-review

- No TBD/TODO left for executors: verification explicitly allows omitting unverifiable docs.
- FAOLEX IDs in Task 1 are labeled as scaffold guesses — must be live-verified.
- `invalidate_bm25_cache` name consistent across Task 4 tests and implementation.
- Facade name `generate_json` consistent; nodes switch import to `app.llm.generate`.
- Cloud URL path: `{base}/chat/completions` — set `CLOUD_LLM_BASE_URL` to include `/v1` when the host needs it (document in `.env.example` comment).
