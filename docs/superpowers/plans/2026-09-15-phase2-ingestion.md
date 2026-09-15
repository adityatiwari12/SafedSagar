# Phase 2 — Ingestion Pipeline Implementation Plan

**Goal:** fetch, parse, chunk, and load 4 real primary-source documents
(one per required source) into Postgres (`source_documents`) and ChromaDB,
end to end, so Phase 3's retrieval node has a real corpus to query.

**Architecture:** a small set of composable scripts under `/ingestion` —
fetch → parse → chunk → embed+load — driven by `source_registry.yaml`.
No web framework involved; these are CLI/batch scripts run once (or
re-run on re-ingestion), not part of the FastAPI request path.

**Tech Stack:** `httpx` (fetch), `pypdf` (PDF text extraction), Python
stdlib `re`/`html.parser` or `beautifulsoup4` (HTML extraction), Ollama's
`nomic-embed-text` (already pulled locally) for embeddings via its HTTP
API, `chromadb` Python client.

**Spec:** `D:\IP-Shakti\CLAUDE.md` (metadata model, source registry seed,
scraping caveats #6), `C:\Users\ASUS\.claude\plans\nested-questing-koala.md`
(Phase 2 roadmap row).

## Global Constraints

- Rate-limited, respectful access to ipindia.gov.in/fssai.gov.in — no
  bulk scraping (CLAUDE.md caveat #6). This phase fetches exactly 4
  documents, one request each, with a real User-Agent and a delay
  between requests.
- Metadata model per chunk: `doc_id, title, authority, jurisdiction,
  doc_type, effective_date, version, section_or_article, source_url,
  last_verified_date, source_text` — real Postgres rows.
- `/corpus/raw` is gitignored (already is); `/corpus/processed` holds
  chunked+tagged JSON.

## Schema correction (before ingestion can work)

Phase 1's `SourceDocument` model made `id` (the PK) hold the document's
`doc_id` directly — i.e. one row per *document*. The metadata model is
actually per *chunk*: a single Act has dozens of citable sections, each
needing its own row with its own `section_or_article` and `source_text`,
while sharing one logical `doc_id`. This wasn't caught in Phase 1 because
no ingestion existed yet to expose it. Fixing now, before any real data
depends on the old shape.

### Task 2.1: Add `doc_id` grouping column, chunk-level `id`

**Files:**
- Modify: `apps/api/app/db/models.py` (`SourceDocument`)
- Create: new Alembic migration in `apps/api/alembic/versions/`

**Change:** `SourceDocument.id` becomes a `String` PK holding a
chunk-level identifier (e.g. `"ipindia-patents-act-1970#s3p"` or
`"...#chunk-0042"` for non-sectioned text). Add `doc_id: Mapped[str]`
(indexed, not unique) holding the logical document identifier shared
across all of that document's chunks — this is what `validate_citations`
(Phase 3) matches a citation against. `title`/`authority`/`jurisdiction`/
`doc_type`/`effective_date`/`version`/`source_url`/`last_verified_date`
stay as document-level fields (duplicated per chunk row — denormalized,
deliberately: chunk rows are what retrieval returns, and each returned
chunk needs its full citation metadata attached without a join).

- [ ] Edit `models.py`: rename existing `id` column's role — keep `id:
      Mapped[str] = mapped_column(String, primary_key=True)` (now a
      chunk id, not a doc id), add `doc_id: Mapped[str] =
      mapped_column(String, nullable=False, index=True)`.
- [ ] `alembic revision --autogenerate -m "source_documents: chunk-level id + doc_id grouping column"`, review the generated migration (table is empty in every environment so far — no data migration needed, just an `ALTER TABLE` adding the column + index).
- [ ] `alembic upgrade head` against the docker-compose Postgres.
- [ ] Update `apps/api/tests/test_models.py`'s `SourceDocument` round-trip test to set both `id` (a chunk id) and `doc_id` (the parent doc id) and assert both round-trip.
- [ ] Run `pytest apps/api/tests -v` — expect all still passing.
- [ ] Commit.

## Source registry

### Task 2.2: `ingestion/source_registry.yaml`

**Files:** Create: `ingestion/source_registry.yaml`

Four entries, using the verified real URLs below (found via live
WebSearch/WebFetch this session, not guessed):

```yaml
sources:
  - doc_id: ipindia-patents-act-1970
    title: "The Patents Act, 1970 (incorporating all amendments till 1-08-2024)"
    authority: "Office of the Controller General of Patents, Designs & Trademarks (India)"
    jurisdiction: india
    doc_type: statute
    source_url: "https://ipindia.gov.in/frontend/pdf/patents/1_113_1_The_Patents_Act__1970___incorporating_all_amendments_till_1-08-2024.pdf"
    format: pdf
    version: "amendments-till-2024-08-01"
    effective_date: null
    last_verified_date: "2026-09-15"

  - doc_id: india-biological-diversity-act-2002
    title: "The Biological Diversity Act, 2002"
    authority: "National Biodiversity Authority / Ministry of Environment, Forest and Climate Change (India)"
    jurisdiction: india
    doc_type: statute
    source_url: "https://www.indiacode.nic.in/bitstream/123456789/21545/1/the_biological_diversity_act,_2002.pdf"
    format: pdf
    version: "2002"
    effective_date: "2003-02-05"
    last_verified_date: "2026-09-15"
    notes: "nbaindia.org's old direct PDF links (nbaindia.org/uploaded/act/...) now 301 to the bare nbaindia.nic.in homepage post domain migration; India Code (indiacode.nic.in) is the live official mirror of the same Act text."

  - doc_id: fssai-ayurveda-aahara-regulations-2022
    title: "Food Safety and Standards (Ayurveda Aahara) Regulations, 2022"
    authority: "Food Safety and Standards Authority of India (FSSAI)"
    jurisdiction: india
    doc_type: regulation
    source_url: "https://fssai.gov.in/upload/notifications/2022/05/62789a20b54bdGazette_Notification_Ayurveda_Aahara_09_05_2022.pdf"
    format: pdf
    version: "2022"
    effective_date: "2022-05-09"
    last_verified_date: "2026-09-15"

  - doc_id: wipo-nagoya-protocol-2010
    title: "Nagoya Protocol on Access to Genetic Resources and the Fair and Equitable Sharing of Benefits Arising from their Utilization to the Convention on Biological Diversity"
    authority: "World Intellectual Property Organization (WIPO) / Convention on Biological Diversity"
    jurisdiction: international
    doc_type: treaty
    source_url: "https://www.wipo.int/wipolex/en/text/594672"
    format: pdf
    version: "2010"
    effective_date: "2014-10-12"
    last_verified_date: "2026-09-15"
```

- [ ] Write the file exactly as above.
- [ ] Commit.

## Fetch

### Task 2.3: `ingestion/fetch.py`

**Files:**
- Create: `ingestion/fetch.py`
- Create: `ingestion/__init__.py` (empty, if running as a package)

**Interface:** a `fetch_all(registry_path: Path, raw_dir: Path,
delay_seconds: float = 3.0) -> list[Path]` function, plus a `if __name__
== "__main__":` CLI entry (`python -m ingestion.fetch`).

Behavior: read `source_registry.yaml`, for each entry download
`source_url` to `<raw_dir>/<doc_id>.<ext>` (ext from `format`) using
`httpx.get` with a real `User-Agent` header (e.g. `"IP-SAKTI-Sahayak-Ingestion/0.1 (SIH hackathon project; contact: team@ipsakti.local)"`), a
15s timeout, and raise on non-200. Sleep `delay_seconds` between
requests (respectful rate limiting per CLAUDE.md caveat #6 — this isn't
a loop hitting one site repeatedly, but keep the pause anyway since it's
cheap and correct practice). Skip re-downloading if the target file
already exists (idempotent re-runs) unless a `--force` CLI flag is passed.

- [ ] Write `ingestion/fetch.py`.
- [ ] Run it for real: `python -m ingestion.fetch` from repo root (need
      a venv with `httpx` and `pyyaml` — reuse `apps/api/.venv` by adding
      these to a new `ingestion/requirements.txt`, or create a separate
      lightweight venv at `ingestion/.venv` — controller's call at
      implementation time based on what's less friction).
- [ ] Verify: all 4 files land in `corpus/raw/`, each >1KB, `file
      corpus/raw/*.pdf` (or PowerShell equivalent) confirms real PDF
      headers, not HTML error pages.
- [ ] Commit `ingestion/fetch.py` + `ingestion/requirements.txt` (NOT the
      downloaded files themselves — `/corpus/raw/` stays gitignored).

## Parse

### Task 2.4: `ingestion/parse.py`

**Files:** Create: `ingestion/parse.py`

**Interface:** `parse_document(raw_path: Path, format: str) -> str`
returning the full extracted plain text. PDF via `pypdf.PdfReader` (join
all pages' `.extract_text()`); if a page's extracted text is suspiciously
short relative to page count (a scanned-image heuristic), log a warning
but don't fail — flag it in the output for a human to notice, since OCR
is out of scope for this phase.

- [ ] Write `ingestion/parse.py`.
- [ ] Run against all 4 raw files, print extracted char count per doc.
- [ ] Verify each extraction is non-trivial (>5000 chars for the Acts,
      which are dozens of pages) and spot-check the first 500 chars of
      one document visually match the real statute text (not garbage/
      mojibake from a bad encoding guess).
- [ ] Commit.

## Chunk

### Task 2.5: `ingestion/chunk.py`

**Files:** Create: `ingestion/chunk.py`

**Interface:** `chunk_text(doc_id: str, full_text: str, target_chars:
int = 1500, overlap_chars: int = 200) -> list[dict]`, returning a list
of `{"section_or_article": str | None, "source_text": str}` dicts.

Behavior: try to detect section markers first via a regex tuned to
Indian statute conventions (e.g. `^\s*(\d+[A-Z]?)\.\s` for "3. " or
"3A. " at line start, or `^Section\s+(\d+)` / `^Article\s+(\d+)`) — if
enough matches are found (heuristic: at least 5 section boundaries
detected), split by section and use the matched number/label as
`section_or_article`, keeping each section as one chunk (further
splitting a section only if it exceeds ~3x `target_chars`, since
citation granularity should stay at the section level where possible —
this is what CLAUDE.md's `validate_citations` node actually checks
against). If section detection doesn't find enough boundaries (e.g. the
Nagoya Protocol's article structure may not match the regex), fall back
to fixed-size sliding-window chunking (`target_chars` with
`overlap_chars` overlap), `section_or_article=None`.

- [ ] Write `ingestion/chunk.py`.
- [ ] Run against all 4 parsed texts, print chunk count + whether
      section-based or fallback splitting was used, per document.
- [ ] Verify by eye: print 2-3 sample chunks from the Patents Act and
      confirm they read as coherent section text, not mid-sentence cuts
      in odd places for the section-based path.
- [ ] Commit.

## Embed + load

### Task 2.6: `ingestion/embed_and_load.py`

**Files:** Create: `ingestion/embed_and_load.py`

**Interface:** `load_document(doc_id: str, registry_entry: dict,
chunks: list[dict]) -> int` (returns rows written), plus a
`if __name__ == "__main__":` driver running the full
fetch→parse→chunk→embed→load pipeline for every registry entry (calling
the functions from Tasks 2.3-2.5 directly rather than shelling out).

Behavior per chunk:
1. Call Ollama's embeddings endpoint (`POST http://localhost:11434/api/embed`, model `nomic-embed-text`, already pulled locally — confirmed via `ollama list`) to get the chunk's vector.
2. Write a `SourceDocument` row to Postgres: `id=f"{doc_id}#{i:04d}"` (or `f"{doc_id}#{section_or_article}"` when a real section label exists, sanitized for safe use as a string PK), `doc_id=doc_id`, plus all the registry entry's document-level metadata fields, `section_or_article`, `source_text`.
3. Upsert the same chunk (id, vector, and a metadata dict of `{doc_id, jurisdiction, doc_type, section_or_article}` for Chroma-side filtering) into a ChromaDB collection named `source_chunks` (create it if missing, via the `chromadb` HTTP client pointed at the docker-compose Chroma container on `localhost:8000`).

Use `apps/api/app/db/base.py`'s `AsyncSessionLocal` (import path
`sys.path`-adjusted or `ingestion` installed alongside `apps/api` — the
controller decides the cleanest import wiring at implementation time; a
plain `sys.path.insert` at the top of the script is acceptable for a
one-off ingestion script, this doesn't need to be production-elegant).

- [ ] Write `ingestion/embed_and_load.py`.
- [ ] Ensure `docker compose -f infra/docker-compose.yml up -d` has both
      postgres AND chroma running (chroma hasn't been used yet since
      Task 1.1 — first real exercise of that container).
- [ ] Run the full pipeline for all 4 documents.
- [ ] Verify: `SELECT doc_id, count(*) FROM source_documents GROUP BY
      doc_id;` in Postgres shows 4 doc_ids with plausible chunk counts
      (tens to low hundreds per Act, fewer for the shorter regulation/
      treaty). Query the Chroma collection's count and confirm it
      matches the Postgres row count exactly (same chunks, both stores).
- [ ] Spot-check one real query: embed a test question via the same
      Ollama endpoint, query Chroma for nearest neighbors, confirm the
      top result's `source_text` is topically relevant (e.g. a
      Section-3(p)-related question returns a chunk actually containing
      "Section 3" or "traditional knowledge" language).
- [ ] Commit `ingestion/embed_and_load.py`.

## Verification (whole phase)

1. `docker compose -f infra/docker-compose.yml ps` — postgres AND chroma
   both healthy/running.
2. `python -m ingestion.fetch && python -m ingestion.embed_and_load`
   (or one combined driver script) runs clean end to end from a fresh
   clone (empty `corpus/raw`, empty `source_documents` table, empty
   Chroma collection).
3. Postgres `source_documents` has 4 distinct `doc_id`s, each with
   `>0` chunk rows, and every row has a non-null `source_text`,
   `source_url`, `jurisdiction`, `doc_type`.
4. Chroma's `source_chunks` collection count equals the Postgres row
   count.
5. A manual similarity query against Chroma for an Ayurveda-IP-relevant
   question returns topically sensible results.

## Notes for Phase 3

`retrieve` (Phase 3) will query this same Chroma collection + do a
keyword/BM25 pass over `source_documents.source_text`, filtered by
`jurisdiction`/`doc_type` — the `doc_id` grouping column added in Task
2.1 is what `validate_citations` matches an LLM's cited `doc_id`/
`section_or_article` against the retrieved chunk set.
