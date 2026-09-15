# Corpus Expansion + Faster Hybrid RAG + Llama Runtime — Design

Status: approved in chat 2026-09-15 (Approach 1; Wave A corpus; local default + optional
cloud Llama). Spec written for review before the implementation plan.

## Context

Phases 1–4 delivered auth/schema, the Phase 2 ingestion pipeline
(`fetch` → `parse` → `chunk` → `embed_and_load`), LangGraph hybrid retrieval + citation
validation, and classifier/router nodes. Phase 5 (frontend) is in progress separately.

The live corpus is only **four** documents in `ingestion/source_registry.yaml`:

- Patents Act 1970 (India)
- Biological Diversity Act 2002 (India, via FAOLEX mirror)
- FSSAI Ayurveda Aahara Regulations 2022 (Wayback mirror)
- Nagoya Protocol 2010 (international)

PRD / CLAUDE.md require national coverage across patents, GI, trade marks, designs,
copyright, plant varieties, drugs/advertising, biodiversity rules, plus international
TRIPS / Paris / PCT / CBD / Budapest / GRATK (not yet in force), and the landmark ABS
case Divya Pharmacy v. Union of India.

Generation today: Ollama `llama3.2` via `apps/api/app/llm/ollama_client.py`, embeddings
`nomic-embed-text`. Retrieval: Chroma vector + Postgres BM25, fused by RRF in `rerank`.

**Known Phase 2 lesson:** many Indian gov URLs return JS-SPA `text/html` shells with
HTTP 200. Every new URL must pass the existing `%PDF` magic-byte check in `fetch.py`
before it is committed to the registry.

## Goals

1. **Breadth:** Wave A authoritative PDFs covering the PRD’s core India IP + ABS +
   drugs spine and the named international treaties, plus Divya Pharmacy.
2. **Depth without scope creep:** no Madrid/Hague deep texts, no pharmacopoeia/CCRAS
   fragments, no extra case-law scrape, no TKDL content (pointer module only).
3. **Faster retrieval** as the corpus grows: stop rebuilding BM25 on every request;
   run vector and BM25 legs in parallel.
4. **Llama effectiveness without fine-tuning:** tighter cite-only prompts, jurisdiction
   lock, optional OpenAI-compatible cloud Llama behind the same `generate_json` facade.
5. **Explicit non-goal:** LoRA/QLoRA fine-tuning in this wave.

## Non-goals

- Fine-tuning Llama (deferred; see Fine-tuning gate)
- Changing the embedding model (would force full re-embed)
- Cross-encoder rerankers, new vector DBs, or agentic multi-source orchestration
- Bulk Indian Kanoon HTML scraping
- Committing raw PDFs (`corpus/raw/` stays gitignored)

## Approach (approved)

**Registry-first + RAG-tight prompts + surgical retrieval speed.**

Reuse the Phase 2 pipeline. Expand `source_registry.yaml` only with verified PDFs.
Add BM25 process cache + `asyncio.gather` for hybrid retrieve. Add optional cloud
provider for generation. Do not fine-tune.

---

## §1 Corpus inventory (Wave A)

### Keep (already registered)

| doc_id | Role |
|---|---|
| `ipindia-patents-act-1970` | India patents statute |
| `india-biological-diversity-act-2002` | India ABS statute |
| `fssai-ayurveda-aahara-regulations-2022` | Ayurveda food regulation |
| `wipo-nagoya-protocol-2010` | International ABS treaty |

### Add — India

| Area | Target | doc_type |
|---|---|---|
| Patents | Patents Rules (2003 as amended / 2024 rules) if stable PDF | `rules` |
| Trade Marks | Trade Marks Act, 1999 (+ Rules if stable) | `statute` / `rules` |
| Designs | Designs Act, 2000 (+ Rules if stable) | `statute` / `rules` |
| GI | Geographical Indications of Goods Act, 1999 (+ Rules if stable) | `statute` / `rules` |
| Copyright | Copyright Act, 1957 (as amended) | `statute` |
| Plant varieties | PPV&FR Act, 2001 | `statute` |
| Drugs | Drugs and Cosmetics Act, 1940 | `statute` |
| Advertising | Drugs and Magic Remedies (Objectionable Advertisements) Act, 1954 | `statute` |
| Biodiversity | BD (Amendment) Act 2023 and/or BD Rules 2024 if stable PDF | `statute` / `rules` |

### Add — International

| Treaty | Note | doc_type |
|---|---|---|
| TRIPS | WTO official text | `treaty` |
| Paris Convention | Stable WIPO/WTO PDF | `treaty` |
| PCT | WIPO | `treaty` |
| CBD | CBD Secretariat PDF (same pattern as Nagoya) | `treaty` |
| Budapest Treaty | WIPO | `treaty` |
| WIPO GRATK (2024) | **Signed, not yet in force** — `notes` must say so; never treat as binding | `treaty` |

### Add — Case law (hand-curated)

| Case | Note |
|---|---|
| Divya Pharmacy v. Union of India (Uttarakhand HC) | One stable PDF URL, or manual drop into `corpus/raw/` with `fetch: false` / skip flag and provenance in `notes`. No Indian Kanoon HTML scrape. |

### Explicitly out of Wave A

Madrid/Hague deep texts, pharmacopoeial/CCRAS sources, additional landmark cases,
TKDL contents, export-market herbal regimes.

---

## §2 Ingestion & URL verification

### Pipeline (unchanged)

```
source_registry.yaml → fetch.py → parse.py → chunk.py → embed_and_load.py
```

### Verification gate (before registry commit)

For each candidate URL:

1. HTTP 200 after redirects
2. Response body starts with `%PDF` (not `text/html`)
3. Size sanity check (roughly > 10 KB)

Mirror fallback order when the official domain fails: **IPO / India Code static PDF →
FAOLEX → Wayback Machine**. Record the reason in `notes` (same pattern as existing BD
Act and FSSAI entries).

### Registry rules

- Required fields unchanged: `doc_id`, `title`, `authority`, `jurisdiction`
  (`india` | `international`), `doc_type`, `source_url`, `format`, `version`,
  `effective_date`, `last_verified_date`
- New optional field: `fetch: false` for hand-placed PDFs (Divya Pharmacy fallback)
- `doc_type` values used in Wave A: `statute` | `rules` | `regulation` | `treaty` |
  `case_law`
- `last_verified_date` = calendar day the URL was actually checked
- Only `source_registry.yaml` (and code/docs) are committed — never raw PDFs

### `fetch.py` change

Honor `fetch: false`: if the target file already exists under `corpus/raw/{doc_id}.pdf`,
skip download; if missing, fail with a clear message telling the operator to place the
file manually. Do not invent content.

### Post-ingest

Re-run embed/load so Chroma `source_chunks` and Postgres `SourceDocument` rows include
every new `doc_id`. Upsert/replace by chunk id / doc_id per existing embed script
behavior.

---

## §3 Llama runtime (local default + optional cloud)

### Keep unchanged

- Embeddings: Ollama `nomic-embed-text` only (stable vectors; no mid-corpus swap)
- Node call shape: `generate_json(prompt)` / `embed(texts)`
- Mechanical `validate_citations` remains the primary anti-hallucination lever

### Provider switch

Config (env / `Settings`):

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `cloud` |
| `OLLAMA_GENERATE_MODEL` | `llama3.2` | Local generate model |
| `CLOUD_LLM_BASE_URL` | unset | OpenAI-compatible base URL |
| `CLOUD_LLM_API_KEY` | unset | Secret; never commit |
| `CLOUD_LLM_MODEL` | unset | e.g. Llama 3.1 8B instruct on Groq/Together/Fireworks |
| `LLM_REASONING_PROVIDER` | optional | If set, only `reason_and_cite` uses this provider; classifiers stay on `LLM_PROVIDER` / ollama |

Implementation sketch:

- Keep `apps/api/app/llm/ollama_client.py`
- Add `apps/api/app/llm/cloud_client.py` (OpenAI-compatible chat completions + JSON
  response format)
- Add `apps/api/app/llm/generate.py` facade that routes `generate_json` by provider
- No LangChain

### Prompt tightening (`reason_and_cite`)

- Jurisdiction lock: only reason over chunks whose jurisdiction matches the routed
  jurisdiction; never blend India and international authority in one answer
- When GRATK chunks appear: state clearly that the treaty is signed but **not yet
  binding**
- Stronger abstention when chunks do not support the claim
- Keep JSON schema: `answer` + `citations[{doc_id, section_or_article}]`

### What we will not do

- LoRA / QLoRA fine-tuning in this wave
- Embedding-model change
- Multi-agent / tool-calling rewrite of the LangGraph

---

## §4 Faster retrieval

### Bottleneck

`retrieve._bm25_search` currently:

1. SELECTs all Postgres chunks matching filters
2. Tokenizes every chunk
3. Builds a fresh `BM25Okapi` index
4. Scores the query

This is acceptable at 4 documents and will dominate latency at Wave A scale. Vector and
BM25 legs also run **sequentially**.

### Changes (surgical, same node)

1. **Process-level BM25 cache** keyed by `(jurisdiction, doc_type)` holding tokenized
   corpus + `BM25Okapi` instance + row id list. Invalidate when:
   - explicit `invalidate_bm25_cache()` is called from embed/load completion, or
   - cached row-count / max `updated_at` (if available) disagrees with a cheap
     Postgres probe
2. **Parallel hybrid:** `asyncio.gather(_vector_search(...), _bm25_search(...))` so
   wall time ≈ max(vector, bm25)
3. **Keep metadata filters** from routers (`jurisdiction`, `doc_type` when known) so
   both legs search a slice
4. **Do not change** RRF fusion or `FINAL_TOP_K` unless LLM context size becomes the
   bottleneck (separate from retrieval latency)

### Out of scope for speed

ANN tuning beyond Chroma defaults, new vector store, cross-encoder rerank,
embedding-model swap.

---

## §5 Fine-tuning gate (deferred)

**Do not fine-tune now.**

Fine-tuning is reconsidered only if, after Wave A corpus + prompt lock + faster
retrieve, a fixed evaluation set (~30 questions spanning India IP types, ABS, and
international treaties) still fails on *reasoning style / structure* while
`validate_citations` already shows correct citations. Citation-grounded legal RAG
almost always needs better corpus and retrieval, not LoRA weights that can drift from
statute text.

If revisited later: prefer small LoRA on instruction-following / JSON schema adherence,
never on memorizing statute text (that belongs in the corpus).

---

## Success criteria

- Every Wave A `doc_id` either (a) fetches as a real PDF through `fetch.py`, or (b) is
  marked `fetch: false` with a manually placed file and documented provenance
- Parse → chunk → embed succeeds for all Wave A docs; Chroma + Postgres both queryable
- Hybrid retrieve wall time improves vs “rebuild BM25 every request” baseline on the
  expanded corpus (BM25 path becomes score-against-cache, not rebuild)
- Answers remain citation-validated; India / international never blended
- `LLM_PROVIDER=ollama` remains the default; cloud path works when configured
- GRATK answers never present the treaty as in-force law

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Gov SPA / HTML-shell URLs | `%PDF` gate; FAOLEX / Wayback mirrors + `notes` |
| Divya Pharmacy PDF unavailable as stable URL | Manual drop + `fetch: false` |
| BM25 cache stale after re-ingest | Invalidate on embed completion + count probe |
| Cloud API key leakage | Env-only secrets; never commit `.env` |
| Larger corpus → noisier retrieval | Jurisdiction / doc_type filters; keep RRF top-k |
| Cloud model ignores JSON schema | Keep `format`/JSON mode; existing fallback message on parse failure |

## Files likely touched (implementation plan will detail)

- `ingestion/source_registry.yaml` — Wave A entries
- `ingestion/fetch.py` — `fetch: false` support
- `apps/api/app/graph/nodes/retrieve.py` — BM25 cache + parallel gather
- `apps/api/app/graph/nodes/reason_and_cite.py` — prompt lock
- `apps/api/app/llm/*` — cloud client + facade
- `apps/api/app/config.py` — new settings
- Tests under `apps/api/tests/` for retrieve cache/parallel behaviour and LLM facade
  routing
- This spec under `docs/superpowers/specs/`

## Implementation order (preview; full plan after spec approval)

1. Verify candidate URLs; write Wave A registry entries (mirrors where needed)
2. Extend `fetch.py` for `fetch: false`; fetch all auto sources; place Divya PDF if needed
3. Parse → chunk → embed Wave A
4. BM25 cache + parallel retrieve + tests
5. Prompt tightening + optional cloud LLM facade + tests
6. Smoke: sample India patent / ABS / international TRIPS questions with citations
