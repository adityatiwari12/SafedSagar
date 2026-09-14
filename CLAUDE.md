# IP-SAKTI Sahayak — Project Brief

SIH Problem Statement 26045 | Ministry of Ayush | All India Institute of Ayurveda (AIIA)

A multilingual, citation-grounded RAG assistant that helps Ayurveda practitioners,
researchers, AYUSH startups/MSMEs and cultivators navigate IP, biodiversity/ABS and
regulatory questions, with India and international jurisdictions kept strictly separate.

Full source PRD: `IP-SAKTI_Sahayak_PRD_Complete_SIH.docx` (Parts I and II). This file is
the buildable distillation of it — read it in full before Phase 2 if something here is
ambiguous, but treat THIS file as the source of truth for scope and architecture decisions,
since the PRD leaves some sections undefined (see "Known gaps" below).

## Core architecture principle — read this first

The PRD's Section 11 diagram (language layer → conversation engine → intent/entity
extraction → classifiers/routers → query planner → retrieval → reranker → LLM reasoning →
evidence validator → answer) is NOT eight microservices. Implement it as **one LangGraph
state graph inside a single FastAPI service.** Do not split this into separate deployable
services — that's scope inflation for a hackathon timeline, not a requirement.

## Stack

- **Backend**: Python, FastAPI, LangGraph for orchestration.
- **Vector store**: ChromaDB.
- **Relational store**: Postgres — users, roles, conversations, escalation queue, audit
  log, and the source/document metadata registry (see Metadata model below).
- **Frontend**: React + TypeScript.
- **Retrieval**: hybrid (vector similarity + BM25/keyword) — legal/statute text needs exact
  section-number and term matches, not just semantic similarity.

### LangGraph node sequence
`classify_product` → `route_jurisdiction` → `route_ip_type` → `retrieve` (hybrid, filtered
by jurisdiction + doc_type) → `rerank` → `reason_and_cite` (LLM constrained to only cite
chunks present in its context) → `validate_citations` (mechanical check: does every cited
doc_id/section actually appear in the retrieved set? strip/flag anything that doesn't —
this is the main anti-hallucination lever) → `score_confidence` → `escalate_if_needed`.

## Repo structure

```
/apps/web          — React+TS frontend
/apps/api          — FastAPI + LangGraph backend
/ingestion          — source_registry.yaml, fetch/parse/chunk scripts
/corpus/raw         — gitignored, downloaded source PDFs
/corpus/processed   — chunked + metadata-tagged JSON
/infra              — docker-compose (postgres, chroma)
CLAUDE.md           — this file
```

## Metadata model (per chunk/document — PRD Section 10)

`doc_id, title, authority, jurisdiction, doc_type, effective_date, version, section_or_article,
source_url, last_verified_date, source_text`. Store this in Postgres as real rows (not just
vector-store metadata) so staleness/re-ingestion can be queried directly.

## RBAC — three roles for MVP, do not add more without a reason

| Role | Covers | Permissions |
|---|---|---|
| **User** | Practitioner / researcher / AYUSH startup / MSME / cultivator (one role — these differ in intake context, not permissions) | Chat, saved history, jurisdiction preference |
| **Facilitator** | Human IP facilitator | Escalation queue, respond, close items |
| **Admin** | Corpus/content + system admin (merged for MVP) | Source registry, re-ingestion triggers, audit log, user management |

## Non-negotiable caveats — do not build against these assumptions

1. **TKDL is not scrapable.** Access is restricted to ~17 patent offices worldwide under
   NDA terms that forbid revealing contents to third parties except as a patent-proceeding
   citation. Build FR-09 as a **pointer/awareness module** ("TKDL prior art likely exists
   for this — contact CSIR-TKDL unit"), never as live retrieval.
2. **The WIPO GRATK Treaty (adopted 24 May 2024) is not yet in force** — it needs 15
   ratifications and has only a handful so far. Present it in the international module as
   "signed, not yet binding," not as active law.
3. **Section 14 accuracy targets (≥90% answer accuracy, ≥95% citation correctness) are
   evaluation goals, not MVP entry criteria.** Don't burn build time chasing them early.
4. **No State Emblem, no claim of official AYUSH branding.** Use a GIGW-style layout
   (accessible, WCAG 2.1 AA-aligned, breadcrumb nav, visible "last verified" dates,
   language switcher in header) but keep a persistent "SIH 2026 Prototype — Not an
   official Government of India website" strip in header/footer.
5. **Bhashini requires portal registration before you can call its API** — start that
   process on day one regardless of when multilingual work is scheduled.
6. Scrape ipindia.gov.in / nbaindia.org / fssai.gov.in search UIs respectfully and
   rate-limited. Don't bulk-scrape Indian Kanoon's HTML — use their API or hand-curate
   ~15–20 landmark cases for MVP (Divya Pharmacy v. Union of India is the obvious ABS one).

## Known gaps in the source PRD — confirm before Phase 3

PRD Sections 6 (**Target Users**) and 8 (**Functional Requirements**) are blank headers in
the source document, yet Section 19's traceability table references FR-02 through FR-12 as
if defined. Below is a DRAFT reconstruction inferred from the traceability table and the
Core User Journey (Section 7) — confirm/edit with your team before relying on it:

| ID | Draft definition | Status |
|---|---|---|
| FR-01 | Conversational intake + minimum clarifying questions | drafted, unconfirmed |
| FR-02 | Product/formulation classification | drafted, unconfirmed |
| FR-03 | IP type detection/routing | drafted, unconfirmed |
| FR-04 | India vs International jurisdiction toggle | drafted, unconfirmed |
| FR-05 | RAG knowledge engine (version-tracked corpus) | drafted, unconfirmed |
| FR-06 | Citation engine | drafted, unconfirmed |
| FR-07 | Confidence indicator + safe abstention | drafted, unconfirmed |
| FR-08 | ABS assistant | drafted, unconfirmed |
| FR-09 | TKDL / prior-art pointer (see caveat #1) | drafted, unconfirmed |
| FR-10 | Query planner / evidence-retrieval orchestration | **undefined in PRD — proposed by inference, needs team sign-off** |
| FR-11 | Human escalation | drafted, unconfirmed |
| FR-12 | Multilingual/voice (Bhashini) | drafted, unconfirmed |

## Source registry seed (`/ingestion/source_registry.yaml`)

| Source | Content | Access |
|---|---|---|
| ipindia.gov.in | Patents Act + 2024 Rules, GI, Trade Marks, Designs, PVP, gazette notifications | Public PDFs |
| iprsearch.ipindia.gov.in | Patent/GI/trademark registry records | Public search UI, rate-limit |
| nbaindia.org / nbaindia.nic.in | Biological Diversity Act, 2024 Rules (effective late Dec 2024), ABS guidance | Public PDFs |
| fssai.gov.in | Ayurveda Aahara Regulations 2022, Category-A lists | Public |
| ayush.gov.in / PCIM&H / CCRAS | Pharmacopoeial standards, classical-text schedules | Public but fragmented — budget real time |
| wipolex (wipo.int) | TRIPS, PCT, Madrid, Hague, Budapest Treaty, CBD, Nagoya, GRATK text | Public, structured |
| Indian Kanoon | Case law | API or hand-curated set only |
| TKDL | — | **Not fetchable — see caveat #1** |

## Build order

0. Confirm FR list + personas with team (see Known gaps above).
1. Postgres schema + auth/RBAC skeleton.
2. Ingestion pipeline against 3–4 real sources, end to end, before touching the LLM layer.
3. LangGraph retrieval + citation core.
4. Classifier/router nodes.
5. Frontend.
6. Escalation queue + facilitator view.
7. GIGW-style UI polish + accessibility pass.
8. One real multilingual path (Hindi only) — don't attempt full Bhashini coverage under
   time pressure.

## Explicitly out of scope for MVP

Knowledge graph (PRD Phase 3), agentic multi-source orchestration (Phase 4), paid-source
connectors (Phase 4), voice interface (Phase 5), automatic IP/regulatory filing. These are
staged *after* the MVP in the source PRD itself — don't parallelize them in.
