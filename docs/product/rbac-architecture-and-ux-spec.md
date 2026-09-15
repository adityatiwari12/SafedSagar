# IP-SAKTI Sahayak — RBAC, Workflows & Feature Architecture

Status: design reference (target architecture). Current backend (see
CLAUDE.md, `apps/api`) implements a 3-role MVP subset of this
(`user`/`facilitator`/`admin`). This document is the fuller model to
build toward — Section 0 states exactly what changes and what stays.

## 0. Reconciliation with the current MVP (read this first)

CLAUDE.md's original RBAC table merged Practitioner/Researcher/
Cultivator/Entrepreneur into one `User` role ("these differ in intake
context, not permissions") and merged all admin functions into one
`Admin` role. That collapse is **still correct** for Practitioner/
Researcher/Cultivator/Entrepreneur — they get the same permissions, only
different dashboard content and intake questions, so they stay one RBAC
role (`user`) with a `persona` profile field, not four database roles.

What's changing from the 3-role model, per this round's requirements:

| Change | Why |
|---|---|
| Split `admin` into `institutional_admin`, `ministry_admin`, `kb_manager` | Least-privilege: a single institution's admin should not touch platform-wide config or another institution's users; knowledge-base governance is a distinct skill/responsibility from user administration. |
| Add `regulatory_expert` as a role parallel to `facilitator` | IP questions and regulatory-compliance questions need different expert reviewers; conflating them under one "facilitator" queue was already an approximation. |
| Add self-service role selection at registration | Explicit ask: "at login/register I should be able to select roles." Only for the roles safe to self-select (see 2.1) — never for admin tiers. |

Resulting roles: `guest` (unauthenticated), `user` (persona: entrepreneur
\| practitioner_researcher \| cultivator), `facilitator`,
`regulatory_expert`, `institutional_admin`, `ministry_admin`,
`kb_manager`. Seven backend roles, not nine — Guest has no DB row and
"AYUSH Entrepreneur/MSME" is the `user` role's default persona, not a
separate role.

---

## 1. Personas — purpose, onboarding, dashboard, permissions

### Guest (unauthenticated)
- **Purpose:** evaluate the tool before committing to an account.
- **Onboarding:** none — landing page only.
- **Dashboard:** none.
- **Visibility:** public info pages (what the tool does, disclaimer,
  sample Q&A), language switcher.
- **Actions:** browse marketing/info pages; cannot submit a question.
- **AI capabilities:** none live — a "try a sample question" carousel of
  pre-canned Q&A is static content, not a live model call (protects
  against anonymous abuse of the LLM/embedding backend).
- **Restrictions:** no query endpoint access, no account data.

### Registered User — persona: AYUSH Entrepreneur/MSME
- **Purpose:** get IP/regulatory/ABS guidance for a specific product or
  innovation they intend to commercialize.
- **Onboarding:** email + password, business name (optional), product
  category interest (optional, seeds first classification), jurisdiction
  preference.
- **Verification:** email verification only (link/OTP). No document
  verification for MVP.
- **Dashboard:** Ask AI, My Products, Assessments, Saved Sources,
  Reports, Expert Requests, Notifications.
- **Data visibility:** own conversations/products/assessments only.
- **Actions:** ask questions, save/export answers, request expert
  escalation, manage own product records.
- **AI capabilities:** full RAG pipeline access (classify → route →
  retrieve → cite → confidence → escalate).
- **Restrictions:** cannot see other users' data; cannot see facilitator/
  admin views; cannot edit the knowledge base.

### Registered User — persona: Practitioner/Researcher
- Same role (`user`), different persona flag. Onboarding adds optional
  affiliation (institution/clinic) and research-area tags.
- **Dashboard:** adds Research Assistant, Prior-Art/TK Discovery, Saved
  Research — same underlying "My Products/Assessments" surfaces relabeled
  for a research framing, not separate infrastructure.
- Same permissions/restrictions as Entrepreneur persona.

### Registered User — persona: Cultivator/Biological Resource Provider
- Same role (`user`), different persona flag. Onboarding adds
  biological-resource type(s) and region/state (relevant to ABS/NBA
  jurisdiction).
- **Dashboard:** adds Biological Resource Records, ABS Guidance, Case
  Status (if they're the resource party in someone else's ABS case),
  Benefit-Sharing Info.
- Same permissions/restrictions as other `user` personas.

### IP Facilitator
- **Purpose:** review AI-flagged/escalated IP questions (patent,
  trademark, GI, copyright, design, trade secret, PCT) a human should
  weigh in on.
- **Onboarding:** professional details (bar/agent registration number if
  applicable, specialization areas), **requires verification** before
  activation.
- **Verification:** Institutional Admin or Ministry Admin reviews
  submitted credentials; account stays `pending_verification` (cannot
  access the facilitator dashboard) until approved.
- **Dashboard:** Assigned Cases, Triage Queue, AI Assessment (read-only
  view of what the AI produced), Sources, Risk Flags, Documents,
  Communication, Review/Corrections, Recommendations, Escalation (to
  Regulatory Expert or Ministry Admin if out of scope), Case Closure.
- **Data visibility:** only cases assigned/available in the shared
  triage queue — never a user's full account, only the specific
  conversation/case.
- **Actions:** claim a case, message the user (case-scoped), correct/
  annotate the AI's answer, close a case, escalate further.
- **AI capabilities:** can re-run/refine a query on the user's behalf
  with elevated retrieval (see full retrieved-chunk set, not just what
  the user saw).
- **Restrictions:** no user management, no knowledge-base edit, no
  visibility into cases not assigned/claimed by them.

### Regulatory Expert
- Mirror of IP Facilitator, scoped to regulatory-compliance questions
  (AYUSH/FSSAI/Drugs & Cosmetics classification, licensing, labelling/
  advertising claims) rather than IP questions.
- **Onboarding/verification:** same pattern as Facilitator (regulatory
  credentials, admin-verified).
- **Dashboard:** Product Classifications Queue, Compliance Cases, AI
  Recommendations, Evidence, Review/Validation, Risk Flags, Expert
  Guidance, Escalation.
- Same data-visibility/action pattern as Facilitator, scoped to
  regulatory (not IP) cases. A case can be routed to both if it spans
  both domains (e.g. "new drug patent + clinical evidence requirement").

### Institutional Admin
- **Purpose:** administers one AYUSH institution's users and cases (e.g.
  a state AYUSH department, an AIIA department) — scoped, not
  platform-wide.
- **Onboarding:** provisioned by a Ministry Admin only — never
  self-registered.
- **Dashboard:** Users (within their institution), Expert Verification
  (approve Facilitators/Regulatory Experts affiliated with their
  institution), Case Oversight (institution's cases), Institution
  Analytics.
- **Data visibility:** users/cases tagged to their institution only.
- **Actions:** approve/reject expert verification requests, suspend a
  user within their institution, reassign a stuck case.
- **Restrictions:** cannot touch the knowledge base, cannot see other
  institutions' data, cannot change platform-wide configuration or
  create Ministry/KB-manager accounts.

### Ministry/Super Admin
- **Purpose:** platform-wide governance (Ministry of Ayush oversight per
  the SIH problem statement's sponsoring body).
- **Onboarding:** provisioned out-of-band (seeded directly in the
  database/by a deployment script) — never self-registered, never
  provisioned by another admin tier.
- **Dashboard:** all Institutional Admin capabilities platform-wide,
  plus: Organisations (create/manage institutions), Platform Analytics,
  Security/Audit Logs (full), Configuration (feature flags, disclaimer
  text, supported languages), Escalation oversight (any case,
  any institution).
- **Data visibility:** everything.
- **Actions:** everything Institutional Admin can do, plus create/remove
  Institutional Admins, KB Managers, and other Ministry Admins;
  platform configuration changes.
- **Restrictions:** still cannot fabricate/bypass citation validation —
  the anti-hallucination mechanism is not a configurable admin toggle.

### Knowledge-Base Manager
- **Purpose:** owns corpus quality — source registry, ingestion,
  versioning, metadata correctness. Distinct from Ministry Admin because
  it's a specialist function (legal/library science), not general
  platform administration.
- **Onboarding:** provisioned by a Ministry Admin only.
- **Dashboard:** Source Registry (Acts/Rules/Treaties/Case Law/
  Notifications), Source Verification (mark last-verified date, flag a
  source as superseded), Metadata Editor (doc_type/jurisdiction/
  effective_date correction), Versioning (track amendments), Ingestion
  Triggers (re-run the pipeline for one or all sources), Indexing Status
  (Postgres row count vs. Chroma vector count — the exact parity check
  used during Phase 2 build), Audit History (who changed what metadata,
  when).
- **Data visibility:** the knowledge base and its own audit trail — not
  user accounts, not case data.
- **Actions:** add/edit/deprecate a source, trigger re-ingestion, correct
  metadata, mark a document superseded (keeps the old version queryable
  but flagged, per the "never silently delete a legal source" principle).
- **Restrictions:** cannot see user PII/case content, cannot approve
  expert verification, cannot change platform config.

---

## 2. Registration

### 2.1 Self-registerable vs. provisioned roles

| Role | Self-registration | Activation |
|---|---|---|
| User (any persona) | Yes | Immediate after email verification |
| IP Facilitator | Yes, as a **request** | Pending until Institutional/Ministry Admin approves |
| Regulatory Expert | Yes, as a **request** | Pending until Institutional/Ministry Admin approves |
| Institutional Admin | No | Provisioned by Ministry Admin |
| Ministry Admin | No | Seeded at deployment, or provisioned by another Ministry Admin |
| Knowledge-Base Manager | No | Provisioned by Ministry Admin |

This is what "select a role at registration" means concretely: the
signup form's role selector shows **User** (with a persona sub-choice),
**IP Facilitator (request)**, and **Regulatory Expert (request)** — the
last two land in `pending_verification` status, functionally a `user`
with no elevated access until approved, and cannot access their target
dashboard until approved. Admin tiers are never in that selector.

### 2.2 Flow

```
Landing → Language select → Sign up / Login
  → Role selector: User | Facilitator (request) | Regulatory Expert (request)
  → [if User] Persona: Entrepreneur/MSME | Practitioner/Researcher | Cultivator
  → Profile (role-specific fields, see 2.3)
  → Email verification
  → [if Facilitator/Regulatory Expert] "Pending verification" holding
    screen instead of dashboard, until an admin approves
  → Consent: Privacy Policy + Terms + "information, not legal advice"
    acknowledgement (all three required checkboxes, not one bundled
    checkbox — DPDP-aligned granular consent)
  → Dashboard
```

### 2.3 Fields per role

| Field | User | Facilitator/Reg. Expert | Notes |
|---|---|---|---|
| Email | Required | Required | Verified via OTP/link |
| Password | Required | Required | 8-72 chars (existing bcrypt bound) |
| Full name | Required | Required | |
| Persona | Required (User only) | N/A | entrepreneur \| practitioner_researcher \| cultivator |
| Business/institution name | Optional | Required | |
| Jurisdiction preference | Optional | N/A | Default answer scope, not a hard restriction |
| Professional registration number | N/A | Required | Bar Council/Patent Agent/professional body number |
| Specialization areas | N/A | Required | Multi-select, drives case-routing |
| Supporting document upload | N/A | Required | Verified manually by an admin before activation |
| Privacy consent | Required | Required | Explicit checkbox, logged with timestamp |
| Terms acceptance | Required | Required | Explicit checkbox, logged with timestamp |
| "Not legal advice" ack | Required | Required | Explicit checkbox, logged with timestamp |

---

## 3. Core user journey

```
User question
  → Language (existing UI language selector; answer language ==
    interface language for MVP, per Build order step 8's Hindi-only scope)
  → Jurisdiction: India | International | Both
      - If the user has a stored jurisdiction_preference, pre-select it
        but let them change it per-question (FR-04's explicit switch —
        never silently overridden, per Phase 4's route_jurisdiction design)
  → Product/context collection (free text — the existing /query question field)
  → Minimum clarifying questions
      - ONLY asked when classify_product returns "unclear" AND the
        question is otherwise answerable — the AI does not ask
        clarifying questions when it already has enough to classify.
        (Concretely: clarifying questions are a follow-up turn triggered
        by product_classification == "unclear", not a mandatory
        pre-question form.)
  → Product classification (classify_product node)
  → Intent detection (route_ip_type node — multi-label)
  → IP / Regulatory / ABS / TK routing (route_ip_type + doc_type filter
    on retrieve)
  → Authoritative RAG (retrieve → rerank → reason_and_cite)
  → Evidence validation (validate_citations)
  → Answer + citations + confidence (score_confidence)
  → Recommended actions (new, Section 4/10 — see Answer UI)
  → Save/export (existing per-conversation save; export as PDF/Markdown)
  → Human escalation when required (escalate_if_needed → visible "Request
    Expert Review" action, pre-filled with the case context)
```

This matches the already-built backend graph (`app/graph/graph.py`)
almost exactly — the two additions this journey implies that don't exist
yet are: (a) a clarifying-question follow-up turn when classification is
unclear, and (b) "Recommended actions" as a distinct answer-UI section
(currently the answer is a single text blob).

---

## 4. Product classification — questions, logic, results

| Category | Trigger signal | Key implication shown to user |
|---|---|---|
| Classical/generic medicine | Formulation matches a First-Schedule text, no novel processing claimed | TK-heavy, faces Section 3(p) patenting bar; defend via TKDL awareness, not patents |
| Patent/proprietary medicine | Proprietary formulation, not classical-text-derived | Patent potential exists; must show novelty over classical/prior art |
| New/non-classical drug | Novel drug requiring safety/efficacy evidence | Genuine patent potential; needs clinical evidence trail; longer regulatory path |
| Phytopharmaceutical | Standardized plant-derived drug, defined process | Phytopharma-specific regulatory pathway (distinct from classical/new-drug) |
| Ayurveda-Aahara/nutraceutical | Food-framed product, no disease-treatment claim | FSSAI Ayurveda-Aahara Regulations apply; no drug claims permitted |
| Cosmetic | External-use, cosmetic claims only | Cosmetic rules under Drugs & Cosmetics Act; no drug/food claims |

**Decision logic:** `classify_product` (existing LLM node) returns one of
these six or `unclear`. When `unclear`, the follow-up turn asks at most
2-3 targeted questions (e.g. "Is this taken orally as a food, or applied
externally?", "Is the formulation from a specific classical text, or a
new combination?") — never a long form.

**Result screen:** classification + one-line rationale + confidence +
"what this means" implication (the right column of the table above) +
link to the relevant regulatory framework's overview page.

---

## 5. Use cases (by domain)

### IP
Patentability screening (Section 3(p) TK-bar check first, before novelty/
inventive-step), prior-art awareness (TKDL pointer per CLAUDE.md caveat
#1 — never live TKDL retrieval), trademark registrability + opposition
procedure, GI eligibility (community/region-linked products), copyright
(labelling/packaging/literary content), design registration, trade
secret posture (when patenting is barred or undesirable), PCT/
international filing pathway overview.

### TK (Traditional Knowledge)
TK identification (is this formulation "in effect, traditional
knowledge" per Section 3(p)?), TKDL/prior-art guidance (pointer/
awareness module ONLY — CLAUDE.md caveat #1: TKDL access is restricted
to ~17 patent offices under NDA; the assistant says "TKDL prior art
likely exists — contact the CSIR-TKDL unit," never retrieves TKDL
content), misappropriation-prevention guidance (documentation practices,
prior-use evidence).

### ABS (Access and Benefit Sharing)
Biological-resource identification (is the input material covered by
the Biological Diversity Act?), applicability determination (domestic
use vs. commercial use vs. research vs. export — different ABS
obligations), authority/process (NBA vs. State Biodiversity Board
depending on applicant type), documentation requirements, benefit-sharing
terms guidance, commercialisation/export implications (this is where the
Divya Pharmacy v. Union of India precedent — now in the corpus — is most
directly relevant).

### Regulatory
Product classification (Section 4), licence requirements by category,
AYUSH/FSSAI/cosmetic-specific requirements, evidence standards (what
proof is needed for a new-drug vs. classical claim), labelling
requirements, advertising/claims restrictions (Drugs & Magic Remedies
Act boundary — no disease-cure claims on Aahara products).

### International
PCT filing overview, TRIPS baseline obligations, CBD/Nagoya Protocol ABS
obligations for cross-border resource use, WIPO GRATK Treaty (explicitly
flagged "signed, not yet binding" per caveat #2 — the reason_and_cite
prompt already enforces this), international trademark (Madrid) and
design (Hague) systems, destination-country market-access notes (India
vs International kept visibly separate per FR-04 — never blended into
one answer).

### Official resources
Direct links/pointers to the Acts, Rules, treaties, and registries in
the corpus (surfaced via the citation list on every answer), plus a
static directory of the actual authorities (IPO, NBA, FSSAI, CDSCO, WIPO)
and where to find their official forms/filing portals.

---

## 6. Dashboards & features (role-wise)

Already detailed per-role in Section 1; this is the feature inventory
each dashboard draws from:

- **Ask AI** — the core `/query` flow (Section 3).
- **Products** — a user's saved product/innovation records (each one is
  effectively a saved classification + conversation thread).
- **Assessments** — the classification + IP/regulatory/ABS implications
  output, saved per product.
- **IP Opportunities** — a derived view: for a given product, which IP
  regimes are actually viable (from accumulated `route_ip_type` results
  across that product's questions).
- **Regulatory Checklist** — derived from `product_classification` +
  regulatory use-case answers, presented as a checklist the user can tick.
- **ABS/TK Checks** — same pattern for the ABS/TK use cases.
- **Documents** — uploaded supporting documents (verification docs for
  experts; optional product documentation for users).
- **Saved Sources** — citations the user has bookmarked across questions.
- **Reports** — exportable summary of a product's full assessment.
- **Expert Requests** — the user's escalation history and status.
- **Notifications** — case status changes, expert responses, verification
  approval/rejection.
- **Case queues, triage, review tooling** — Facilitator/Regulatory Expert
  dashboards (Section 1).
- **Source registry, ingestion, indexing status** — KB Manager dashboard
  (Section 1), directly reusing the Postgres-row-count-vs-Chroma-count
  parity check pattern already used to verify Phase 2 ingestion.
- **User/org management, verification, analytics, config, audit** —
  Admin-tier dashboards (Section 1).

---

## 7. RBAC matrix

Legend: V=View, C=Create, E=Edit, D=Delete, A=Approve, S=Assign,
X=Escalate, R=Export. Blank = no access.

| Resource | User | Facilitator | Reg. Expert | Inst. Admin | Ministry Admin | KB Manager |
|---|---|---|---|---|---|---|
| Own profile | V,C,E | V,C,E | V,C,E | V,C,E | V,C,E | V,C,E |
| Other users' profiles | | | | V (own inst.) | V,E,D | |
| Products (own) | V,C,E,D,R | | | | | |
| Products (any, assigned case) | | V | V | V (own inst.) | V | |
| Assessments (own) | V,C,R | | | | | |
| AI queries | C | C | C | C | C | |
| Documents (own) | V,C,E,D | | | | | |
| Documents (case-scoped) | | V,C | V,C | V (own inst.) | V | |
| IP analysis | V | V,E | V | V | V | |
| Regulatory analysis | V | V | V,E | V | V | |
| ABS/TK/prior-art | V | V,E | V,E | V | V | |
| Cases | C,X (own) | V,E,S,X (assigned/queue) | V,E,S,X (assigned/queue) | V,S (own inst.) | V,S,X (all) | |
| Expert review | | E | E | A | A | |
| Knowledge base | V (via citations) | V | V | | V | V,C,E,D |
| Users | | | | V,E (own inst.) | V,C,E,D (all) | |
| Roles | | | | | C,E,D | |
| Verification | | | | A (own inst.) | A (all) | |
| Analytics | | | | V (own inst.) | V (all) | V (KB metrics) |
| Audit logs | | | | V (own inst.) | V (all) | V (KB actions) |
| Configuration | | | | | V,E | |

---

## 8. Expert case workflow

```
AI answer generated
  → score_confidence: low, OR user explicitly requests review
  → User clicks "Request Expert Review" (pre-fills case with the
    conversation, retrieved chunks, and AI's answer/citations as context)
  → Case created (status: open), routed to IP Facilitator queue or
    Regulatory Expert queue based on route_ip_type output (a case
    touching both gets duplicated into both queues, linked)
  → Triage: any facilitator/expert in the right queue can claim it
    (status: in_progress, assigned_to set)
  → Review: expert reads the AI's answer + full retrieved-chunk set
    (not just what the user saw — experts get the wider candidate pool)
  → [optional] Information request: expert asks the user a follow-up
    question (status: awaiting_user_input); user responds, case
    resumes review
  → Expert guidance: written response, referencing the AI's answer
    (endorse / correct / replace) — always distinct from the AI answer
    in the UI, labelled "Expert Response," never blended
  → User notified
  → Closure (status: closed, closed_at set, resolution summary required)
  → Feedback: user rates the resolution (optional, 1-5 + free text)
```

Every transition writes an audit-log entry (`AuditLogEntry` — already in
the Phase 1 schema): who, what changed, when. This workflow is what
Phase 6 ("Escalation queue + facilitator view") builds — Phase 4's
`escalate_if_needed` node already produces the trigger signal
(`escalate: bool`, `escalation_reason: str`) this workflow consumes; it
just doesn't persist a `EscalationItem` row yet (noted as a known gap
after Phase 4).

---

## 9. AI/RAG requirements

Already implemented (Phases 3-4), stated here as the standing
requirement this design must not regress:

```
User → Language/Jurisdiction → classify_product → route_jurisdiction →
route_ip_type → retrieve (hybrid vector+BM25, jurisdiction/doc_type
filtered) → rerank (RRF) → reason_and_cite (LLM, constrained to
retrieved chunks + doc_type-aware framing) → validate_citations
(mechanical accept/reject, the anti-hallucination lever) →
score_confidence (deterministic) → escalate_if_needed → Answer
```

- Never fabricate: enforced structurally, not by prompt instruction
  alone — `validate_citations` mechanically strips any citation not
  present in the retrieved set, verified live in Phase 3/4 testing
  (correctly rejected 4/4 fabricated citations in one test case).
- Version-tracked sources: `SourceDocument.version`,
  `effective_date`, `last_verified_date` already in the schema.
- Safe abstention: `reason_and_cite`'s prompt explicitly instructs
  abstention over guessing; `escalate_if_needed` escalates on low
  confidence, zero validated citations, or unclear classification.
  Exact abstention copy for the UI: *"I could not find sufficient
  authoritative evidence to answer this reliably. This has been flagged
  for human expert review."*
- India/International separation: `jurisdiction` is a first-class filter
  on retrieval (never blended); `jurisdiction_source` (explicit vs.
  inferred) is already surfaced in the API response for the UI to show
  "(assumed India — change jurisdiction)" when inferred.

---

## 10. Answer UI structure

```
┌─────────────────────────────────────────┐
│ Short answer (1-2 sentences)             │
├─────────────────────────────────────────┤
│ Classification: <product category>       │
│ Jurisdiction: India | International       │
│   [explicit | inferred - change]          │
├─────────────────────────────────────────┤
│ IP implications                          │
│ Regulatory implications                  │
│ ABS implications                         │
│ TK implications                          │
│ (only sections with actual content show) │
├─────────────────────────────────────────┤
│ Next steps (recommended actions)         │
├─────────────────────────────────────────┤
│ Confidence: ●●●○○ Medium        [ⓘ]      │
├─────────────────────────────────────────┤
│ Sources                                  │
│  [1] Patents Act, 1970 - Section 3(p)    │
│      ipindia.gov.in ↗                    │
│  [2] ...                                 │
├─────────────────────────────────────────┤
│ [Request Expert Review]                  │
├─────────────────────────────────────────┤
│ ⚠ This is information, not legal advice. │
│   Consult a qualified professional for   │
│   binding guidance.                      │
└─────────────────────────────────────────┘
```

The disclaimer bar is persistent (footer-pinned within the answer card),
not a one-time dismissible modal — matches CLAUDE.md's "persistent
'information, not legal advice' disclaimer" governance requirement.

---

## 11. Privacy & security

- **Authentication:** existing JWT bearer (HS256, already hardened —
  Phase 1 final review fixed the weak-secret and bcrypt-72-byte issues).
- **RBAC/authorization:** `require_role()` dependency, extended to the
  7-role set (Section 0); case-scoped authorization (a Facilitator can
  only act on cases assigned to them or in their queue, checked at the
  query layer, not just at the route layer).
- **Encryption:** TLS in transit (deployment concern); at-rest encryption
  for the Postgres volume in production (not needed for local hackathon
  dev, flagged for the real deployment).
- **Consent:** three explicit checkboxes at registration (Section 2.2),
  each logged with a timestamp in `AuditLogEntry`.
- **Data minimisation:** intake forms only collect what a persona's
  dashboard actually uses (Section 2.3) — no speculative fields.
- **Confidential document isolation:** a user's uploaded documents are
  never visible to another user, and visible to a Facilitator/Regulatory
  Expert ONLY for a case they're assigned to — enforced by a
  case-scoped access check on the document-read path, not by trusting
  the frontend to hide the link.
- **Audit logs:** every case-state transition, every verification
  approval/rejection, every admin action on another user's account.
- **Retention:** conversation/product data retained per the user's
  account lifetime; a data-export and account-deletion path required for
  DPDP alignment (not yet built — flagged for Phase 2).
- **Cross-user isolation:** the RBAC matrix (Section 7) is the
  authorization source of truth — "Users must never access another
  user's confidential IP/product/research/business data" is enforced by
  every case/document/product query being scoped to `user_id ==
  current_user.id` OR an explicit case-assignment check, never by a
  blanket role check alone.

---

## 12. Roadmap

### MVP (current + this design's registration/role work)
Registration with role selection (Section 2), 7-role RBAC, India/
International switch, product classification, IP/regulatory/ABS/TK
guidance, RAG with citations/confidence/abstention (built, Phases 1-4),
expert escalation *decision* (built) + queue *persistence* (Phase 6, not
yet built), User/Facilitator/Regulatory Expert/Admin dashboards, English
+ Hindi (Hindi not yet built — Phase 8).

### Phase 2
Knowledge graph (products/ingredients/laws/sections/patents/regulations/
jurisdictions), expanded case law corpus, better prior-art search, more
AYUSH regulations ingested, more Indian languages, data-export/
account-deletion (DPDP), Institutional Admin org-management UI.

### Phase 3
Agentic multi-source orchestration, voice interface, full Bhashini
integration, paid-source connectors (e.g. a licensed case-law database),
advanced registry integration (live IPO/NBA registry lookups), country-
specific market-access detail for major export destinations.

---

## 13. Core database entities (additions to the existing Phase 1 schema)

Existing (`apps/api/app/db/models.py`): `User`, `Conversation`,
`Message`, `EscalationItem`, `AuditLogEntry`, `SourceDocument`.

Additions this design implies:

- **`User`** — extend `role` enum to the 7 roles (Section 0); add
  `persona` (nullable, only meaningful for `role=user`), `verification_status`
  (`none | pending | approved | rejected`, meaningful for facilitator/
  regulatory_expert), `institution_id` (FK, nullable — set for
  Institutional Admin and institution-affiliated experts).
- **`Institution`** (new) — `id, name, created_by_ministry_admin_id`.
- **`Product`** (new) — `id, user_id, name, description,
  product_classification, jurisdiction, created_at`. A user's saved
  product record; a `Conversation` can reference one.
- **`Conversation`** — add `product_id` (nullable FK).
- **`VerificationRequest`** (new) — `id, user_id, role_requested,
  submitted_documents, status, reviewed_by_id, reviewed_at`.
- **`EscalationItem`** — already exists (Phase 1); Phase 6 wires it to
  real writes. Add `queue` (`ip` \| `regulatory`) and
  `resolution_summary` to match the workflow in Section 8.
- **`Document`** (new) — `id, owner_user_id, case_id (nullable),
  file_ref, visibility_scope, created_at` — the case-scoped isolation
  in Section 11 depends on `visibility_scope` + `case_id` being checked
  on every read.

---

## 14. System architecture

Unchanged from CLAUDE.md's core principle: **one LangGraph-style state
graph inside one FastAPI service** (hand-rolled per `app/graph/graph.py`
— see that file's docstring for why it's not the literal `langgraph`
package). This design adds application-layer routers (users, cases,
verification, knowledge-base admin) around the same service — still one
deployable backend, not new microservices.

```
┌─────────────────────────────────────────────┐
│              React + TS frontend             │
│  (role-aware routing/dashboards per Section 6)│
└───────────────────┬───────────────────────────┘
                     │ HTTPS/JSON, JWT bearer
┌───────────────────▼───────────────────────────┐
│                 FastAPI service                │
│  auth/  query/  cases/  verification/  kb/     │  <- routers
│  graph/ (classify→route→retrieve→rerank→       │
│          reason_and_cite→validate→confidence→  │
│          escalate)                             │
│  llm/   (ollama_client / cloud_client facade)  │
└──────┬───────────────────┬─────────────────────┘
       │                   │
┌──────▼──────┐   ┌────────▼────────┐   ┌─────────────┐
│  Postgres    │   │    ChromaDB      │   │   Ollama    │
│ (relational, │   │ (vector search,  │   │ (local LLM  │
│  RBAC, audit)│   │  source_chunks)  │   │  + embed)   │
└──────────────┘   └──────────────────┘   └─────────────┘
```

---

## 15. Screen-by-screen structure (application map)

- **Public:** Landing, About/How-it-works, Sample Q&A, Privacy Policy,
  Terms, Login, Register (role selector).
- **User (any persona):** Dashboard, Ask AI (chat), Product detail
  (classification + assessments + IP opportunities + regulatory
  checklist + ABS/TK checks), Products list, Saved Sources, Reports,
  Expert Requests (list + detail/thread), Notifications, Profile/Settings.
- **Facilitator / Regulatory Expert:** Dashboard (queue + assigned),
  Case detail (AI assessment, sources, risk flags, documents,
  communication thread, review/correction form, escalate/close actions),
  Verification status (their own, if still pending).
- **Institutional Admin:** Dashboard, Users (list + detail), Expert
  Verification queue, Case Oversight, Institution Analytics.
- **Ministry Admin:** everything Institutional Admin has (platform-wide
  toggle), Organisations, Platform Analytics, Audit Logs, Configuration.
- **Knowledge-Base Manager:** Dashboard, Source Registry (list + detail/
  edit), Ingestion Triggers + status, Metadata Editor, Audit History.

---

## 16. Edge cases & failure scenarios

| Scenario | Handling |
|---|---|
| LLM produces unparseable JSON | `reason_and_cite` already catches this — falls back to "could not produce a well-formed answer" + escalation, not a 500 (verified live in Phase 3). |
| Model cites a chunk it wasn't given | `validate_citations` strips it — verified live, 4/4 fabricated citations correctly rejected in Phase 4 testing. |
| Zero retrieval hits | `reason_and_cite` returns the "no relevant sources" fallback immediately, without calling the LLM. |
| User asks an out-of-scope (non-Ayurveda-IP) question | Verified live: correctly answered "I don't have information," zero citations, low confidence, `escalate=true`. |
| Facilitator/Regulatory Expert account never verified | Stays in `pending_verification`; dashboard shows a status page, not case data — never silently grants access. |
| Two experts try to claim the same case | Optimistic lock on `assigned_to` (first write wins, second gets a "already claimed" response) — not yet built, flagged for Phase 6. |
| A source becomes legally superseded | KB Manager marks it superseded (not deleted) — old citations to it remain valid historical record, new retrieval excludes it. |
| Ollama/Chroma unavailable | `/query` should return a 503 with a clear "assistant temporarily unavailable" message, not a raw 500 — not yet implemented as explicit handling, flagged. |
| User requests jurisdiction "Both" | Run the graph twice (india + international), present as two visibly separate answer cards — never merge into one blended answer (FR-04). |
| Institutional Admin tries to verify an expert outside their institution | RBAC-denied — verification approval is institution-scoped for Institutional Admin, platform-wide only for Ministry Admin. |

---

## 17. Feature acceptance criteria (representative sample)

- **Role selection at registration:** signup form shows exactly User/
  Facilitator(request)/Regulatory Expert(request); selecting Facilitator
  or Regulatory Expert routes to a document-upload step and results in
  `verification_status=pending`; the user cannot reach a
  facilitator/expert dashboard until an admin sets `approved`.
- **Explicit jurisdiction switch:** changing the jurisdiction toggle
  before submitting a question changes `jurisdiction_source` to
  `explicit` in the API response and is never silently overridden by
  inference (already true in the backend; UI must surface the toggle,
  not just accept a default).
- **Safe abstention:** any question where `confidence_level == "low"`
  displays the exact abstention copy from Section 9, not a hedge buried
  in prose.
- **Case isolation:** a Facilitator hitting a case-detail URL for a case
  not assigned to them and not in an open queue gets a 403, not a 404
  (403 is honest about why; 404 would be acceptable too as an
  information-hiding choice — pick one and be consistent).
- **Citation traceability:** every citation shown in the UI is clickable
  through to `source_url`, and every non-null citation in a response
  corresponds to a `validated_citations` entry — never a
  `rejected_citations` entry rendered as if trusted.

---

## Open decision this document does NOT resolve

Expanding `UserRole` from 3 values to 7 is a real Postgres enum
migration and a breaking change to whatever the frontend (currently
being built in the `phase5-frontend` worktree / already shipped in `v1`)
assumes about roles. This document specifies the *target* model: it does
not implement the migration. Before writing that migration, confirm with
whoever owns the frontend work that the 3-role assumption isn't already
load-bearing in shipped UI code.
