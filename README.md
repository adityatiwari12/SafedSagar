
# IP-SAKTI Sahayak

Citation-grounded assistant for **Ayurveda intellectual property, biodiversity / ABS, and
regulatory guidance**, built for SIH Problem Statement 26045 (Ministry of Ayush / AIIA).

> **SIH 2026 Prototype — not an official Government of India website.** No State Emblem
> claim beyond a GIGW-style layout. See [Non-negotiable caveats](#non-negotiable-caveats).

India and international jurisdictions are kept strictly separate throughout. Every answer
is constrained to citations mechanically verified against the chunks actually retrieved for
that query — see [How answers are grounded](#how-answers-are-grounded).

## Contents

- [Architecture](#architecture)
- [Stack](#stack)
- [Repo layout](#repo-layout)
- [Quick start](#quick-start) — full stack: Docker, Ollama, API, Web, translation sidecar
- [LLM provider (local/cloud)](#llm-provider-localcloud)
- [API reference](#api-reference)
- [RBAC](#rbac)
- [Multilingual support](#multilingual-support)
- [Chat features](#chat-features)
- [How answers are grounded](#how-answers-are-grounded)
- [Testing](#testing)
- [Non-negotiable caveats](#non-negotiable-caveats)
- [Known gaps / scope decisions](#known-gaps--scope-decisions)

## Architecture

One FastAPI service, one hand-rolled sequential graph (deliberately not the `langgraph`
package — its dependency chain needs native extensions this machine's Windows Application
Control policy blocks; see the comment in `apps/api/pyproject.toml`). Every `/chat` request
runs the same nine-node pipeline:

```
classify_product → route_jurisdiction → route_ip_type → retrieve (hybrid: vector + BM25)
  → rerank (RRF) → reason_and_cite (LLM, constrained to retrieved chunks)
  → validate_citations (mechanical: is every cited doc_id/section actually retrieved?)
  → score_confidence → escalate_if_needed
```

Multilingual is a translation layer wrapped *around* this pipeline, not a change to it — a
non-English query is translated to canonical English before `classify_product`, and the
canonical English answer is translated back after `escalate_if_needed`. The graph itself,
retrieval, and citation validation are English-only throughout. See
[Multilingual support](#multilingual-support).

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React + TypeScript + Vite + Tailwind (`apps/web`) |
| Backend | FastAPI, hand-rolled LangGraph-shaped state graph (`apps/api`) |
| Vector store | ChromaDB (REST v2 API — not the `chromadb` Python package; see `ingestion/requirements.txt`) |
| Relational store | Postgres — users/RBAC, conversations/messages, escalation queue, audit log, source-document metadata registry |
| Retrieval | Hybrid: vector similarity (ChromaDB) + BM25 (`rank-bm25`, over Postgres-stored chunk text), fused with Reciprocal Rank Fusion |
| Embeddings | `nomic-embed-text` via Ollama |
| Reasoning LLM | `llama3.2` via Ollama (default); optional OpenAI-compatible cloud provider slot (`app/llm/cloud_client.py`) for a quality upgrade without local-hardware latency |
| Translation | AI4Bharat IndicTrans2 (with an NLLB-200 fallback), served by a separate Docker container (`services/indictrans2-sidecar`) — see [why](#multilingual-support) |
| Language detection | `py3langid` (pure Python, in-process, no sidecar needed) |
| Ingestion | `ingestion/` — `source_registry.yaml` + fetch/parse/chunk/embed/load pipeline |

## Repo layout

```
apps/web                     — React+TS frontend (Ministry of Ayush–styled, GIGW/UX4G conventions)
apps/api                     — FastAPI backend
  app/graph/                 — the 9-node pipeline + shared GraphState
  app/chat/                  — /chat, /escalations, /conversations
  app/translation/           — language detection, translation service, glossary, validator
  app/auth/, app/cases/,
  app/admin/, app/query/     — auth/RBAC, facilitator case queue, admin, legacy single-shot /query
  app/llm/                   — Ollama + cloud LLM clients, provider facade
  app/db/                    — SQLAlchemy models, Alembic migrations
services/indictrans2-sidecar — translation model server (own Docker container, own Python version)
ingestion/                   — source_registry.yaml + fetch/parse/chunk/embed/load scripts
corpus/raw, corpus/processed — downloaded/processed source documents (gitignored)
infra/                       — docker-compose (Postgres, ChromaDB, translation sidecar)
docs/                        — architecture notes, language support matrix, product specs
```

## Quick start

Five things need to be running: Postgres, ChromaDB, Ollama, the FastAPI backend, and the
Vite dev server. The translation sidecar is optional (non-English chat degrades gracefully
without it — see [Multilingual support](#multilingual-support)).

### 1. Docker services (Postgres + ChromaDB + translation sidecar)

```bash
cd infra
docker compose up -d
```

Starts `postgres:16` (`:5432`), `chromadb/chroma` (`:8000`), and the translation sidecar
(`:8600`, builds on first run — see `services/indictrans2-sidecar/README.md` for what it
needs and why it's a separate container). Bring up just the two required services with
`docker compose up -d postgres chromadb` if you want to skip the sidecar for now.

The sidecar runs real IndicTrans2 if you set `HF_TOKEN` in `infra/.env` (after accepting
the gate on the two `ai4bharat/indictrans2-*-dist-200M` model pages on Hugging Face);
without it, it auto-falls-back to NLLB-200. See the sidecar README for the one-time setup.

### 2. Ollama

Install from [ollama.com](https://ollama.com), then pull the two models this stack uses:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
ollama serve
```

`ollama serve` must be running before the API starts — `/chat` calls it synchronously for
every classification/reasoning/embedding step.

### 3. API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate        # Windows; source .venv/bin/activate on Linux/Mac
pip install -e ".[dev]"
cp .env.example .env          # set a real JWT_SECRET (32+ chars, not the placeholder)
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Health check: http://127.0.0.1:8001/health. Interactive API docs:
http://127.0.0.1:8001/docs.

### 4. Web

```bash
cd apps/web
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8001
npm install
npm run dev
```

Open http://127.0.0.1:5173, register a user, and start chatting. `VITE_USE_MOCK_CHAT=false`
in `.env.example` means it talks to the real API by default.

### Hardware notes

This stack was built and tested CPU-only, with `llama3.2` as the practical local-model
ceiling for reasoning (a 20B "thinking" model was tried and reverted — see
`apps/api/.env.example`'s note — 67s and unreliable JSON on a trivial prompt on this
hardware). If RAM is tight, don't run the translation sidecar as an always-on background
service — start it only when testing non-English chat.

## LLM provider (local/cloud)

Every LLM call in the graph (`classify_product`, `condense_query`, `route_jurisdiction`,
`route_ip_type`, `reason_and_cite`) goes through one facade, `app/llm/generate.py`, which
picks between two backends:

| Provider | Setting | What it is |
| --- | --- | --- |
| `ollama` (default) | `LLM_PROVIDER=ollama` | Local `llama3.2` via Ollama — everything stays on this machine |
| `cloud` | `LLM_PROVIDER=cloud` | Any OpenAI-compatible `/chat/completions` endpoint (Groq, OpenRouter, a hosted vLLM/TGI instance, ...) |

**Switching:** set `LLM_PROVIDER=cloud` plus `CLOUD_LLM_BASE_URL`, `CLOUD_LLM_MODEL`, and
`CLOUD_LLM_API_KEY` in `apps/api/.env` (see `.env.example` for the full list, including
`CLOUD_LLM_JSON_MODE` and `LLM_FALLBACK_TO_LOCAL`). A cloud provider selected without
`CLOUD_LLM_BASE_URL`/`CLOUD_LLM_MODEL` set fails fast at API startup with a clear error —
unless `LLM_FALLBACK_TO_LOCAL` is on, in which case it logs a loud warning instead and runs
on Ollama, so a misconfigured optional provider never takes the whole API down.

**Recommended setup — cloud for reasoning only:** rather than flipping every call to cloud,
set just `LLM_REASONING_PROVIDER=cloud` and leave `LLM_PROVIDER=ollama`. This spends cloud
calls only on `reason_and_cite` (the final-answer call, where quality matters most) while
`classify_product`/`condense_query`/`route_*` — frequent, latency-sensitive, categorical
calls — stay local and free.

**Reliability:** cloud calls get a bounded retry with backoff on transient failures (429,
5xx, timeouts); a 4xx auth/validation error is never retried. Some OpenAI-compatible
providers reject `response_format: {"type": "json_object"}` outright — that's detected and
retried once without it, parsing JSON out of the (possibly ```json-fenced) response text.
The API key is never written to a log line or exception message.

**Fallback:** if the cloud provider still fails after its retry budget (`LLM_FALLBACK_TO_LOCAL=true`,
the default), that call falls back to local Ollama rather than failing the request — an
expired key or a network drop shouldn't kill a demo. Every `/chat` response reports which
model actually answered via `answered_by: {provider, model, fallback_used}`, so a fallback is
always visible, never silent.

**DPDP / privacy note:** with `LLM_PROVIDER=cloud` (or `LLM_REASONING_PROVIDER=cloud`), the
user's question text and the retrieved legal/regulatory chunks are sent to the configured
third-party endpoint to generate that answer. With the local Ollama default, none of that
data leaves this machine. Don't point a real user's traffic at a cloud provider without
knowing who that provider is and what their data-handling terms are.

## API reference

All endpoints except `/health`, `/auth/register`, and `/auth/login` require a bearer token
(`Authorization: Bearer <token>` from `/auth/login`).

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/auth/register` | Create an account (`role`: user / facilitator / regulatory_expert) |
| POST | `/auth/login` | OAuth2 password flow → bearer token |
| GET | `/auth/me` | Current user profile |
| POST | `/chat` | Main conversational endpoint — see [Chat features](#chat-features) |
| POST | `/escalations` | User-initiated escalation to a human facilitator |
| GET | `/conversations` | List the current user's past conversations (titled, most-recent-first) |
| GET | `/conversations/{id}/messages` | Full turn-by-turn history for one conversation |
| GET | `/cases` | Facilitator/admin: open escalation queue |
| POST | `/cases/{id}/claim` | Facilitator claims a case |
| POST | `/cases/{id}/close` | Facilitator closes a case with a resolution summary |
| GET | `/admin/users` | Admin: user list |
| GET | `/admin/stats` | Admin: corpus/usage stats |
| POST | `/language/detect` | Detect a text's language among the 13 supported codes |
| POST | `/translate` | Direct text translation (used internally by `/chat`; also standalone) |
| POST | `/query` | Legacy single-shot query endpoint (no conversation threading, no clarifying-question flow) — superseded by `/chat` |

### `/chat` request/response

```jsonc
// Request
{
  "conversationId": null,           // or an existing conversation's id to continue it
  "text": "Can I patent a classical Ayurvedic formulation?",
  "jurisdiction": "india",          // "india" | "international"
  "language": "hi",                 // optional — omit to auto-detect
  "answers": null                   // set when answering a clarifying-question round
}
```

```jsonc
// Response (fields below detected_language are additive - see docs/multilingual-architecture.md)
{
  "conversationId": "...",
  "clarifying_questions": null,     // non-null only when product classification is still unclear
  "classification": { "product_type": "...", "ip_type": "..." },
  "jurisdiction": "india",
  "answer": "...",                  // localized if language != en, else canonical English
  "citations": [ { "doc_id": "...", "title": "...", "section_or_article": "...", "source_url": "...", "last_verified_date": "..." } ],
  "confidence": 0.86,
  "confidence_band": "high",        // high (>=0.7) | medium (>=0.4) | low
  "escalate_recommended": false,
  "next_steps": ["..."],
  "abs_tk_flags": { "biological_resource_likely": true, "traditional_knowledge_likely": true, "note": "..." },
  "detected_language": "hi",
  "canonical_query": "...",         // English-translated query
  "canonical_answer": "...",        // English answer before translation
  "translation_status": "verified", // verified | not_needed | failed | unavailable
  "needs_human_review": false,      // translation-quality flag, distinct from escalate_recommended
  "answered_by": { "provider": "ollama", "model": "llama3.2", "fallback_used": false } // null on turns
                                     // that short-circuit before reason_and_cite runs - see
                                     // "LLM provider (local/cloud)" above
}
```

## RBAC

Three roles for MVP — see `apps/api/app/db/models.py` for the enum and
`docs/product/rbac-architecture-and-ux-spec.md` for the full design:

| Role | Covers | Permissions |
| --- | --- | --- |
| `user` | Practitioner / researcher / AYUSH startup / MSME / cultivator | Chat, saved history, jurisdiction/language preference |
| `facilitator` | Human IP facilitator | Escalation queue (`/cases`), claim/close |
| `regulatory_expert` | Domain expert reviewer | Same queue access as facilitator |
| `admin` | Corpus/content + system admin | User list, corpus/usage stats |

`persona` (entrepreneur / practitioner_researcher / cultivator) is separate from `role` —
it drives intake framing only, never permissions. An admin-approval gate for
facilitator/regulatory_expert self-registration was built, then disabled for the demo (see
the docstring on `VerificationStatus` in `models.py`) — the schema is ready to re-enable it.

## Multilingual support

13 languages: English, Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati, Kannada,
Malayalam, Punjabi, Odia, Assamese, Urdu (RTL). Full design, model-choice rationale, and
what's deferred: **`docs/multilingual-architecture.md`** and
**`docs/language-support-matrix.md`**.

Short version: a non-English query is detected (`py3langid`, in-process) and translated to
canonical English by the translation sidecar before touching the existing English-only RAG
pipeline; the answer is translated back and validated (section/rule/article references and
URLs must survive translation unchanged) before being returned. If the sidecar isn't
running, or validation fails, the response falls back to canonical English with
`needs_human_review: true` — it never silently returns a translation it can't verify.

This is a real scope increase over CLAUDE.md's own build order (which scopes multilingual
to Hindi-only for the MVP via Bhashini) — flagged explicitly in the architecture doc, not
hidden.

## Chat features

- **Conversation memory** — follow-up questions ("what does that mean for me?") resolve
  against prior turns in the same conversation, not just the latest message.
- **Chat history** — `apps/web/src/chat/ChatHistorySidebar.tsx` lists past conversations by
  title (derived from the first message) and lets you reopen one, re-rendering it exactly
  as originally shown (citations, classification, confidence) via a stored response
  snapshot, not a live re-query.
- **Guided intake** — for someone who doesn't know how to phrase their question,
  `GuidedIntakeForm` asks three short questions (what have you made/researched, what's it
  for, what do you want to know) and composes them into a proper opening message; the
  existing pipeline takes it from there.
- **One clarifying round, max** — if `classify_product` can't tell what the product is, the
  user is asked a fixed set of clarifying questions exactly once per fresh attempt, never
  repeatedly.
- **ABS / TK awareness** — flags likely biological-resource and traditional-knowledge
  angles (ABS approval, TKDL prior-art pointer) without ever claiming to retrieve TKDL
  contents live (TKDL is not scrapable — see [caveats](#non-negotiable-caveats)).
- **Escalation** — either automatic (`escalate_if_needed`, on low confidence / no validated
  citations / unclear classification) or user-initiated at any time.

## How answers are grounded

`reason_and_cite` is constrained to only the chunks `retrieve`/`rerank` actually surfaced,
using bracket citations (`[1]`, `[2]`) mapped back to chunk `doc_id`/`section_or_article` by
index — never by trusting a model-emitted doc_id string. `validate_citations` then
mechanically checks every citation's `(doc_id, section_or_article)` pair against the
retrieved set and strips anything that doesn't match. This is the main anti-hallucination
lever, and it runs strictly before any translation — see
[Multilingual support](#multilingual-support).

## Testing

```bash
# API
cd apps/api && .venv\Scripts\python.exe -m pytest -q

# Web
cd apps/web && npm test
```

## Non-negotiable caveats

1. **TKDL is not scrapable.** FR-09 is a pointer/awareness module only — never live
   retrieval. Access is restricted to ~17 patent offices worldwide under NDA.
2. **The WIPO GRATK Treaty (adopted 24 May 2024) is not yet in force** — presented as
   "signed, not yet binding," never as active law.
3. **Section 14 accuracy targets (≥90% answer accuracy, ≥95% citation correctness) are
   evaluation goals, not entry criteria** for this build.
4. **No State Emblem, no official AYUSH branding claim** — GIGW-style layout with a
   persistent "SIH 2026 Prototype" strip in header/footer.
5. Sources are scraped respectfully and rate-limited, or hand-curated where an API isn't
   available (Indian Kanoon case law: ~15–20 hand-curated landmark cases, not bulk-scraped).

## Known gaps / scope decisions

- **Multilingual scope** exceeds CLAUDE.md's Hindi-only MVP plan (13 languages, NLLB-200
  instead of Bhashini) — see [Multilingual support](#multilingual-support) for why and
  what's still deferred (semantic translation validation, vetted glossary translations, a
  multilingual eval suite, Bhashini integration itself).
- **Translation sidecar** needs to actually be running for non-English answers to be
  translated — see `services/indictrans2-sidecar/README.md`.
- **FR-01 through FR-12** were blank headers in the source PRD; the draft reconstruction
  used to build this repo is in the project's CLAUDE.md and should be confirmed with the
  full team before Phase 3 work.
- Full functional/product specs live under `docs/product/`; implementation-phase specs and
  plans under `docs/superpowers/`.

## Branch

`v1` is the primary development line for this milestone.
