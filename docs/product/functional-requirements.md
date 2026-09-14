# IP-SAKTI Sahayak — Functional Requirements & Target Users (confirmed)

PRD.md Sections 6 (Target Users) and 8 (Functional Requirements) shipped as
blank headers. CLAUDE.md's "Known gaps" section drafted a reconstruction
from the traceability table (Section 19) and Core User Journey (Section 7).
**Confirmed as-is by the team on 2026-09-14** — this doc is now the FR spec
of record; CLAUDE.md's table is superseded by this file.

## Target Users (PRD Section 6)

Maps 1:1 to the RBAC roles in CLAUDE.md — these differ in intake context,
not permissions, so they collapse to one role:

| Persona | RBAC Role |
|---|---|
| Ayurveda practitioner | User |
| Researcher | User |
| AYUSH startup / MSME | User |
| Cultivator | User |
| Human IP facilitator | Facilitator |
| Corpus/content + system admin | Admin |

## Functional Requirements (PRD Section 8)

| ID | Definition | Status |
|---|---|---|
| FR-01 | Conversational intake + minimum clarifying questions | confirmed |
| FR-02 | Product/formulation classification | confirmed |
| FR-03 | IP type detection/routing | confirmed |
| FR-04 | India vs International jurisdiction toggle | confirmed |
| FR-05 | RAG knowledge engine (version-tracked corpus) | confirmed |
| FR-06 | Citation engine | confirmed |
| FR-07 | Confidence indicator + safe abstention | confirmed |
| FR-08 | ABS assistant | confirmed |
| FR-09 | TKDL / prior-art pointer (see CLAUDE.md caveat #1 — pointer/awareness only, never live retrieval) | confirmed |
| FR-10 | Query planner / evidence-retrieval orchestration | confirmed |
| FR-11 | Human escalation | confirmed |
| FR-12 | Multilingual/voice (Bhashini) — MVP scope is Hindi text only, per CLAUDE.md Build order step 8 | confirmed |

## Traceability

Unchanged from PRD Section 19 — each FR above maps to the SIH requirement
row of the same name in that table.
