# IP-SAKTI Sahayak — Full RBAC/Permission/Case Architecture

Status: approved design, supersedes the "Open decision" at the bottom of
`rbac-architecture-and-ux-spec.md` and extends that document rather than
replacing it — Sections 3-10, 14-17 of that doc (core journey, product
classification, use cases, expert workflow, AI/RAG requirements, answer
UI, screen map, edge cases, acceptance criteria) still apply unchanged.
This document is the schema/permission/case-model layer underneath them.

Written after a live requirements exchange that reconciled a much larger
proposed model (11 roles, generic Permission engine, Organization,
Case/Product/ResearchProject/KnowledgeRecord/Evidence/ExpertReview/
AuditEvent as first-class entities, TK visibility tiers, separation of
duties) against what this repo had already designed and partially built.
Section 0 records the decisions; the rest is the resulting architecture.

## 0. Reconciliation decisions (this session)

| Question | Decision | Why |
|---|---|---|
| Split Practitioner/Researcher/Startup/TK-Holder into 4 roles? | **No — keep merged** as `user` + `persona` (`entrepreneur` \| `practitioner_researcher` \| `cultivator`) | Per the existing design and the new spec's own matrix, these personas have near-identical permissions; they differ in dashboard framing and intake questions, not authorization. Splitting them would 4x the nav/dashboard surface for zero permission difference. |
| Add a third expert tier? | **Yes — `legal_expert`** alongside `facilitator` and `regulatory_expert` | Facilitator resolves routine IP cases; Legal Expert is reserved for escalated/high-risk/ambiguous/complex-international/ABS-sensitive/sensitive-TK cases only, never a direct user-facing queue. |
| Admin split model? | **Keep the existing 3-way split**: `institutional_admin` (org-scoped) / `ministry_admin` (platform-wide) / `kb_manager` (corpus-only) | Already designed for least-privilege-by-scope. A separate `super_admin` role was not added — instead, the new spec's core rule ("infra admin must never get legal-approval authority") is enforced structurally: **no admin-tier role is ever granted `review.approve` / `review.modify` / `review.reject`**, regardless of tier. System administration and legal decision-making are separated by permission grant, not by adding a role. |
| Build scope this pass | **Everything in the spec**, phased (Section 10) | Acknowledged as multi-session. Phase 1 (this session's concrete deliverable) is the foundation: permission engine + organizations + migration of existing endpoints. Phases 2-9 build on it incrementally. |

### Final role set (8 backend roles + guest)

`guest` (unauthenticated, no DB row), `user` (persona-based), `facilitator`,
`legal_expert`, `regulatory_expert`, `institutional_admin`,
`ministry_admin`, `kb_manager`.

This resolves `rbac-architecture-and-ux-spec.md`'s "Open decision": the
`UserRole` enum grows from today's 4 values (`user` / `facilitator` /
`regulatory_expert` / `admin`) to these 8, and single-role-per-user
(`users.role`) becomes multi-role (`user_roles` join table, Section 2).

---

## 1. Core principle (unchanged from CLAUDE.md, restated because it now
governs a bigger surface)

```
USER → USER_ROLES → ROLES → ROLE_PERMISSIONS → PERMISSIONS → RESOURCE + ACTION
```
is the primary authorization model. A role hierarchy (admin tiers,
expert tiers) exists only for *permission inheritance/seeding
convenience* — no code path ever does `if role == "ministry_admin" or
role == "super_admin"` string-chains. Every protected action checks a
permission key, resolved through the user's roles, scoped by
organization/ownership/sensitivity. UI hiding is a courtesy, never the
enforcement boundary — every check below has a server-side counterpart.

---

## 2. Schema — permission engine

```
roles
  id (pk), name (unique, e.g. "facilitator"), description, created_at

permissions
  id (pk), key (unique, e.g. "case.create"), resource, action, description

role_permissions
  role_id (fk roles), permission_id (fk permissions)
  PK (role_id, permission_id)

user_roles
  user_id (fk users), role_id (fk roles)
  organization_id (fk organizations, NULLABLE)
  PK (user_id, role_id, organization_id)
```

`organization_id` on `user_roles`, not on `users`: a role can be
org-scoped (`institutional_admin` for Organization A) while the same
person holds an unscoped role elsewhere (e.g. also a plain `user`). NULL
`organization_id` means the role applies platform-wide (`ministry_admin`,
`kb_manager`, `legal_expert`, `facilitator`, `regulatory_expert`, or a
`user` role with no org affiliation).

**Migration path (expand → migrate → contract, not a single destructive
cut):**
1. Add the four tables above + `organizations`/`organization_members`
   (Section 3). Seed `roles` (8 rows) and `permissions` (catalog, Section
   4) and `role_permissions` (matrix, Section 4).
2. Backfill: for every existing `users` row, insert one `user_roles` row
   from its current `role` column. Existing `admin` rows map to
   `ministry_admin` (the superset of current unrestricted admin
   behavior) — **flagged for manual post-migration review**, since the
   old flat `admin` role never distinguished institutional/ministry/KB
   scope and a script cannot infer which any given admin account should
   actually be.
3. `users.role` stays in the schema, marked deprecated in a code comment,
   until every call site reads `user_roles` instead (Section 5). Dropped
   in a follow-up migration once nothing references it — not in the same
   migration, so a bad cutover is recoverable without a data-loss
   rollback.

---

## 3. Schema — organizations

```
organizations
  id (pk), name, org_type (enum: institution | startup | other),
  created_by_user_id (fk users, nullable), created_at

organization_members
  user_id (fk users), organization_id (fk organizations)
  PK (user_id, organization_id)
```

Supersedes the earlier design's narrower `Institution` concept — a
startup/MSME is also an "organization" for scoping purposes (its
Products/Cases are org-scoped the same way an institution's are), not a
special case.

---

## 4. Permission catalog + role matrix (seed data)

Catalog (from the requested spec, kept as-is — these are genuinely
resource+action, not page names):

```
ai:        ai.ask, ai.translate, ai.view_sources, ai.view_citations, ai.view_reasoning
case:      case.create, case.view_own, case.view_queue, case.edit, case.assign,
           case.escalate, case.close
product:   product.create, product.view, product.edit, product.delete
research:  research.create, research.search_prior_art, research.save_evidence,
           research.export
tk:        tk.create, tk.view_own, tk.view_assigned, tk.view_public, tk.edit,
           tk.set_visibility
review:    review.view, review.approve, review.modify, review.reject, review.escalate
knowledge: source.create, source.edit, source.verify, source.deprecate, source.publish
org:       org.create, org.view, org.manage_members
admin:     users.manage, roles.manage, permissions.manage, organizations.manage,
           system.configure, audit.view
analytics: analytics.personal, analytics.organization, analytics.national
```

Role → permission matrix (✓ = granted; scope enforcement — org/ownership/
assignment — happens in `can_access_resource`, Section 5, not here):

| Permission | user | facilitator | legal_expert | regulatory_expert | inst_admin | ministry_admin | kb_manager |
|---|---|---|---|---|---|---|---|
| ai.* | ✓ | ✓ | ✓ | ✓ | — | — | — |
| case.create | ✓ | — | — | — | — | — | — |
| case.view_own | ✓ | — | — | — | — | — | — |
| case.view_queue | — | ✓ (ip queue) | ✓ (legal-escalation queue only) | ✓ (regulatory queue) | ✓ (own org) | ✓ (all) | — |
| case.edit / case.assign | — | ✓ | ✓ | ✓ | — | — | — |
| case.escalate | ✓ | ✓ | — | ✓ | — | — | — |
| case.close | — | ✓ | ✓ | ✓ | — | — | — |
| product.* | ✓ (own) | — | — | — | — | — | — |
| research.* | ✓ (own) | — | — | — | — | — | — |
| tk.create / tk.edit / tk.set_visibility | ✓ (own) | — | — | — | — | — | — |
| tk.view_assigned | — | ✓ (assigned/granted only) | ✓ (assigned/granted only) | — | — | — | — |
| **review.approve/modify/reject** | — | ✓ (own queue) | ✓ (own queue) | ✓ (own queue) | **—** | **—** | **—** |
| review.escalate | — | ✓ | — | ✓ | — | — | — |
| source.create / source.edit | — | — | — | — | — | — | ✓ |
| source.verify / source.publish | — | — | — | — | — | — | ✓ (SoD-checked, Section 7) |
| org.manage_members | — | — | — | — | ✓ (own org) | ✓ (all) | — |
| users.manage | — | — | — | — | ✓ (own org) | ✓ (all) | — |
| roles.manage / permissions.manage | — | — | — | — | — | ✓ | — |
| system.configure | — | — | — | — | — | ✓ | — |
| audit.view | — | — | — | — | ✓ (own org) | ✓ (all) | ✓ (KB actions only) |
| analytics.personal | ✓ | — | — | — | — | — | — |
| analytics.organization | — | — | — | — | ✓ | ✓ | — |
| analytics.national | — | — | — | — | — | ✓ | ✓ (KB metrics only) |

Bold row is the structural enforcement of "infra/system admin ≠ legal
decision maker" (Section 0): every admin-tier column is blank there, by
construction — not by convention that a future seed edit could quietly
break unnoticed (a unit test asserts it, Section 9).

---

## 5. Authorization service

`apps/api/app/authz/service.py` (new module):

```python
async def load_authz_context(user: User, db: AsyncSession) -> AuthzContext:
    """One query per request (via FastAPI dependency, cached on the
    request), not one query per permission check."""

def has_permission(ctx: AuthzContext, key: str, *, organization_id: UUID | None = None) -> bool
def can_access_resource(ctx: AuthzContext, resource: HasOwnerAndScope) -> bool
def can_perform_action(ctx: AuthzContext, resource, action: str) -> bool
```

- `has_permission`: does any of the user's roles (optionally scoped to
  `organization_id`) grant this permission key.
- `can_access_resource`: ownership (`resource.owner_user_id ==
  ctx.user_id`) OR organization membership match OR an explicit
  assignment/grant (case `assigned_to_user_id`, TK `knowledge_record_access`
  row) OR the resource's own visibility is `public`. This is where TK
  sensitivity and case-queue scoping live — a permission alone
  (`case.view_queue`) is necessary but not sufficient without the queue
  match.
- `can_perform_action`: `has_permission` AND `can_access_resource` AND
  resource-state rules (e.g. `case.close` only from a status that allows
  closing; `review.approve` only by the case's own assigned reviewer,
  never by any other queue-holder).

FastAPI dependency `require_permission(key: str)` replaces
`require_role(*roles)` at every route. `require_role` is deleted, not
kept as a fallback — every existing call site (`app/cases/router.py`,
`app/admin/router.py`) is migrated in Phase 1, not left on the old
mechanism alongside the new one (two parallel authorization systems is
worse than either alone).

---

## 6. Core entities (Phases 2-5)

```
cases
  id, user_id, organization_id (nullable), conversation_id (nullable),
  product_id (nullable), research_project_id (nullable),
  question, language, product_classification, ip_domain, jurisdiction,
  regulatory_issues (json), abs_tk_flags (json),
  retrieved_evidence (json), ai_analysis (json), citations (json),
  confidence_score, confidence_level,
  risk_level (enum: low | medium | high),
  status (enum: open | in_progress | awaiting_user_input | escalated |
          resolved | closed),
  queue (enum: ip | regulatory | legal, nullable),
  assigned_to_user_id (nullable), resolution_summary,
  created_at, closed_at
```
Supersedes `EscalationItem` (folds its columns in). **Behavior change
flagged explicitly**: today only escalated conversations get a persisted
row; this spec's Section 17/21 ("everything revolves around Case," not
"User → Chatbot → Answer") means every question becomes a `Case` row,
low/medium-risk ones auto-`resolved`. This is the single largest volume
change in this design — noted so it isn't a silent surprise later.

```
products               (id, organization_id?, owner_user_id, name, description,
                         product_classification, jurisdiction, ip_status json,
                         regulatory_status json, abs_tk_status json, timestamps)

research_projects      (id, owner_user_id, organization_id?, title, description,
                         formulation_ref, invention_notes, timestamps)

knowledge_records       (id, owner_user_id, organization_id?, knowledge_name,
                         traditional_use, plant_resource, region, community,
                         description,
                         visibility (enum: private | restricted | public,
                                     default 'private'),
                         timestamps)

knowledge_record_access (knowledge_record_id, grantee_user_id?,
                         grantee_role? (facilitator | legal_expert |
                         regulatory_expert), PK(knowledge_record_id, grantee_user_id))

documents               (id, owner_user_id, case_id?, organization_id?, file_ref,
                         doc_kind, visibility_scope (enum: owner | case |
                         organization | public), created_at)

evidence                (id, research_project_id?, case_id?, owner_user_id,
                         source_type, source_ref, title, relevance_note,
                         claims_note, created_at)

expert_reviews           (id, case_id, reviewer_user_id, reviewer_role,
                         action (enum: approve | modify | reject |
                         request_info | escalate), notes,
                         previous_state json, new_state json, created_at)

verification_requests    (id, user_id, role_requested, organization_id?,
                         submitted_documents json,
                         status (enum: pending | approved | rejected),
                         reviewed_by_user_id?, reviewed_at, created_at)
```

`knowledge_record_access` is the ACL for `visibility = restricted` —
"Assigned Facilitator" / "Authorized Expert" in the original ask means a
*specific* grant per record, not "any facilitator can see any restricted
TK record." `private` = owner only, no exceptions. `public` = anyone
(including guest) — never the default (enforced at the DB default and at
the create-endpoint validator, so a client can't POST past it).

---

## 7. Audit events

`AuditLogEntry` (actor_user_id, action, detail json) is upgraded to:

```
audit_events
  id, actor_user_id?, actor_role, action, resource_type, resource_id,
  previous_state (json), new_state (json), reason?, created_at
```

Every state-changing endpoint in Sections 5-6 writes one row: role
approvals/rejections, case status transitions, expert review actions,
source publish/verify/deprecate, admin user/role management, consent
checkboxes at registration. `AuditLogEntry` stays as-is for its existing
rows (read-only, historical); nothing back-migrates old rows into the
new shape, since `detail` (freeform json) can't be reliably decomposed
into `previous_state`/`new_state` after the fact.

---

## 8. Separation of duties — enforced, not documented

- **Admin ≠ legal decision-maker**: structural (Section 4's blank
  `review.*` cells for every admin-tier role), asserted by a unit test
  over the seeded `role_permissions` table so a future seed-data edit
  that violates it fails CI, not just code review.
- **Curator ≠ approver for the same source**: `source.publish` on a
  given `doc_id` is rejected (403, not silently allowed) when the
  calling user's id matches the most recent `source.create`/`source.edit`
  actor recorded in that source's `audit_events` — i.e. one KB Manager
  drafts, a *different* KB Manager (or a future dedicated verifier
  permission) publishes. Enforced in the KB router at write time, not a
  UI convention.
- **Facilitator ≠ Legal Expert routing**: `case.queue = legal` is only
  reachable via `case.escalate` when `risk_level == high` OR an explicit
  ambiguous/complex/ABS-sensitive/sensitive-TK flag is set on the case —
  checked server-side in the case-service, not left to whichever queue a
  client's request happens to name.

---

## 9. Tests (Phase-1-adjacent, not deferred to "later")

- `test_authz_matrix.py`: for every (role, permission) pair, assert
  `has_permission` matches Section 4's table exactly, including the
  "admin tiers never get review.*" invariant.
- Per-router 403 tests: an authenticated user with no matching permission
  gets 403 on every protected route (not 404, not a silent empty list).
- Org isolation test: a `user` in Organization A cannot `case.view_own`
  a Case belonging to a user in Organization B even with a guessed UUID.
- TK visibility test: `private` record invisible to everyone but owner;
  `restricted` visible only to the exact grantees in
  `knowledge_record_access`; `public` visible to guest.
- Migration backfill test: every pre-migration `users.role` value has
  exactly one corresponding `user_roles` row post-migration, none
  dropped.

---

## 10. Build order (this session builds Phase 1; Phases 2-9 are
tracked separately, not attempted in one pass)

1. **Foundation** (this session): `roles`/`permissions`/`role_permissions`/
   `user_roles`/`organizations`/`organization_members` tables + Alembic
   migration + backfill; permission catalog + role matrix seed; `authz`
   service (`has_permission`/`can_access_resource`/`can_perform_action`);
   migrate `app/auth`, `app/cases`, `app/admin` routers off `require_role`
   onto `require_permission`; `roles.manage`/`users.manage` admin
   endpoints (list/assign/revoke roles, list/create organizations).
2. Case model: `cases` table supersedes `EscalationItem`; every question
   creates a Case; `legal_expert` queue + routing rule (Section 8);
   `expert_reviews` + review actions wired to the case-review endpoints.
3. `products` / `research_projects` / `evidence` — ownership+org-scoped
   CRUD routers.
4. `knowledge_records` (TK) + `knowledge_record_access` ACL; cultivator
   persona dashboard wiring.
5. `documents` model, case/org-scoped visibility.
6. `audit_events` (Section 7), wired into every state-changing endpoint
   from Phases 1-5.
7. `verification_requests` flow: facilitator/regulatory_expert/
   legal_expert self-registration-as-request + institutional/ministry
   admin approval UI.
8. Frontend: role-aware navigation shell + per-role dashboard modules,
   reusing existing chat/case components — not 8 separate apps.
9. Ministry/government analytics: aggregated, privacy-preserving queries
   only (no per-user/per-case drill-down for `ministry_admin`'s
   analytics views, even though the role technically has `case.view_queue`
   for oversight — the *analytics* surface specifically stays aggregate).

Tests (Section 9) land alongside Phase 1, not appended at the end.
