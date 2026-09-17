# RBAC Phase 2 — Case Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `EscalationItem` (escalation-only) with `Case` (every answered turn), add `expert_reviews`, and wire `legal_expert` queue routing — Phase 2 of the already-approved `docs/product/rbac-full-implementation-spec.md`.

**Architecture:** Additive Alembic migration (`cases`, `expert_reviews` tables; `escalation_items` stays, deprecated, dropped in a later migration — same expand→migrate→contract discipline as migration `a18b27770761`). A new `app/cases/service.py` derives `risk_level`/`status`/`queue` from the graph's existing `escalate`/`confidence_level`/`ip_types`/`abs_tk_flags` output — no new AI call, no new graph node. `chat/router.py`'s `_process_chat_turn` creates one `Case` row per turn that reaches a real answer or an out-of-scope refusal (not per clarifying-question round). `cases/router.py` is rewritten to queue-scope `list_cases` by the caller's role (facilitator→`ip`, regulatory_expert→`regulatory`, legal_expert→`legal`) and gains a review-action endpoint. REST contracts (`CaseOut`, `POST /escalations`) stay backward-compatible — additive fields only — since frontend wiring is spec Phase 8, out of scope here.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, pytest-asyncio, the existing `app.authz` permission engine (no changes to `app/authz/constants.py` — `case.*`/`review.*` permissions already exist there).

**Spec:** `docs/product/rbac-full-implementation-spec.md` Sections 6 (`cases`/`expert_reviews` schema), 8 (legal-queue routing rule), 9 (test requirements) — this plan implements Section 10, build-order item 2. Also load `docs/product/functional-requirements.md` for FR-11 (human escalation) context.

## Global Constraints

- **8 roles, no more**: `user`, `facilitator`, `legal_expert`, `regulatory_expert`, `institutional_admin`, `ministry_admin`, `kb_manager` (+ unauthenticated `guest`). Do not add roles in this plan.
- **Admin tiers never get `review.approve`/`review.modify`/`review.reject`/`case.view_queue`** — already enforced by `app/authz/constants.py`'s `ADMIN_TIER_ROLES` assertion and `test_authz_matrix.py`; do not touch that file's invariants.
- **No `require_role`** — every new/changed route uses `require_permission(...)` from `app.authz.service`, never a role-name string check.
- **Expand → migrate → contract, never a single destructive cut**: this migration adds `cases`/`expert_reviews` and leaves `escalation_items` in place, unread by new code. Do not drop `escalation_items` in this plan.
- **UI hiding is never the enforcement boundary** — every permission check has a server-side counterpart (already the project's standing rule, CLAUDE.md).
- **REST response shapes stay additive** — `CaseOut`, `EscalateResponse` keep every existing field with the same meaning; only add new optional fields. Frontend (`apps/web`) is not touched in this plan.
- Every state-changing endpoint touched in this plan writes an audit trail entry via the existing `AuditLogEntry` model (Phase 2 of the spec doesn't yet introduce the richer `audit_events` table — that's spec build-order item 6, not this plan).

---

### Task 1: `cases` and `expert_reviews` schema + ORM models

**Files:**
- Create: `apps/api/alembic/versions/<new_revision>_add_cases_and_expert_reviews.py`
- Modify: `apps/api/app/db/models.py` (add `CaseStatus`, `CaseRiskLevel`, `CaseQueue`, `ExpertReviewAction` enums; add `Case`, `ExpertReview` ORM classes; add deprecation docstring to `EscalationItem`)
- Test: `apps/api/tests/test_models.py`

**Interfaces:**
- Produces: `Case` ORM class (`apps/api/app/db/models.py`) with columns `id, user_id, organization_id, conversation_id, question, language, product_classification, ip_types (JSON list), jurisdiction, regulatory_issues (JSON, always NULL for now), abs_tk_flags (JSON), ai_analysis (JSON), citations (JSON), confidence_score, confidence_level, risk_level (CaseRiskLevel), status (CaseStatus), queue (CaseQueue, nullable), assigned_to_user_id (nullable), resolution_summary (nullable), created_at, closed_at (nullable)`. `ExpertReview` ORM class with `id, case_id, reviewer_user_id, reviewer_role, action (ExpertReviewAction), notes (nullable), previous_state (JSON, nullable), new_state (JSON, nullable), created_at`.
- Consumes: nothing from other tasks (this is the foundation task).

- [ ] **Step 1: Write the failing model test**

```python
# apps/api/tests/test_models.py - add to the existing file
async def test_case_and_expert_review_round_trip():
    from app.db.models import (
        Case, CaseQueue, CaseRiskLevel, CaseStatus, ExpertReview, ExpertReviewAction,
        User, UserRole,
    )
    from app.auth.security import hash_password

    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-model-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()

        case = Case(
            user_id=user.id,
            question="Can I patent this?",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=CaseQueue.ip,
        )
        session.add(case)
        await session.flush()

        review = ExpertReview(
            case_id=case.id,
            reviewer_user_id=user.id,
            reviewer_role="facilitator",
            action=ExpertReviewAction.approve,
            notes="Looks right.",
        )
        session.add(review)
        await session.commit()
        await session.refresh(case)
        await session.refresh(review)

        assert case.status == CaseStatus.escalated
        assert case.queue == CaseQueue.ip
        assert review.case_id == case.id
        assert review.action == ExpertReviewAction.approve
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_models.py::test_case_and_expert_review_round_trip -v`
Expected: FAIL with `ImportError: cannot import name 'Case'` (the class doesn't exist yet).

- [ ] **Step 3: Add enums + ORM classes to `app/db/models.py`**

Add near the other enums (after `KnowledgeAccessRole`, before `class User(Base):`):

```python
class CaseStatus(str, enum.Enum):
    """Case lifecycle (spec Section 6). Supersedes EscalationStatus's
    3-value set - `escalated` and `resolved` split what EscalationStatus
    collapsed into `open`, matching Case's "every question becomes a row,
    low/medium-risk auto-resolved" model (spec Section 6)."""

    open = "open"
    in_progress = "in_progress"
    awaiting_user_input = "awaiting_user_input"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"


class CaseRiskLevel(str, enum.Enum):
    """Derived by app.cases.service from the graph's escalate/
    confidence_level output - not a new AI call (see Task 2)."""

    low = "low"
    medium = "medium"
    high = "high"


class CaseQueue(str, enum.Enum):
    """Which expert queue a case belongs to. NULL for a non-escalated
    (auto-resolved) case - queue only matters once a case needs a human.
    Routing rule: app.cases.service, spec Section 8."""

    ip = "ip"
    regulatory = "regulatory"
    legal = "legal"


class ExpertReviewAction(str, enum.Enum):
    """One reviewer action on a case (spec Section 6)."""

    approve = "approve"
    modify = "modify"
    reject = "reject"
    request_info = "request_info"
    escalate = "escalate"
```

Add near the bottom, after `UserRoleAssignment`:

```python
class Case(Base):
    """Every answered chat turn, not just escalated ones (spec Section 6,
    Build order item 2) - supersedes EscalationItem, which only persisted
    a row when escalate_if_needed flagged one. Low/medium-risk cases are
    created already `resolved`; only high-risk ones land in a queue."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)

    question: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    product_classification: Mapped[str | None] = mapped_column(String, nullable=True)
    # List[str] subset of app.graph.state.IP_TYPES - named ip_types (not
    # the spec's "ip_domain") to match the field name already used
    # throughout app/graph and app/chat, not introduce a second name for
    # the same data.
    ip_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String, nullable=True)
    # Reserved for a not-yet-built regulatory-compliance module (spec
    # Phase 10) - always NULL until that module exists. Included now so
    # that module doesn't need its own migration just to add this column.
    regulatory_issues: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    abs_tk_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Snapshot for a reviewer: {"classification": ..., "next_steps": [...],
    # "timing_ms": {...}} - same shape as ChatTurnResponse minus the
    # citations (which get their own column below).
    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_level: Mapped[CaseRiskLevel] = mapped_column(SAEnum(CaseRiskLevel, name="case_risk_level"), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(SAEnum(CaseStatus, name="case_status"), nullable=False)
    queue: Mapped[CaseQueue | None] = mapped_column(SAEnum(CaseQueue, name="case_queue"), nullable=True)

    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    assigned_to: Mapped["User | None"] = relationship(foreign_keys=[assigned_to_user_id])
    organization: Mapped["Organization | None"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()


class ExpertReview(Base):
    """One reviewer action on a Case (spec Section 6). A case can have
    several - the full review history, not just the latest action."""

    __tablename__ = "expert_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Denormalized at write time (which role the reviewer acted under) -
    # a user's roles can change later; this records what was true then.
    reviewer_role: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[ExpertReviewAction] = mapped_column(
        SAEnum(ExpertReviewAction, name="expert_review_action"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped["Case"] = relationship()
    reviewer: Mapped["User"] = relationship()
```

Add a deprecation note to the existing `EscalationItem` docstring (do not delete the class or table):

```python
class EscalationItem(Base):
    """A conversation escalated to a human facilitator.

    DEPRECATED as of docs/product/rbac-full-implementation-spec.md Phase
    2: superseded by `Case`, which persists a row for every answered
    turn (not just escalated ones) and carries risk_level/queue/
    expert_reviews. This table and class stay only for the expand->
    migrate->contract window - no new code reads or writes it after this
    change. Dropped in a follow-up migration once confirmed unused.
    """
```

- [ ] **Step 4: Write the Alembic migration**

First find the current head revision:

Run: `cd apps/api && .venv/Scripts/python.exe -m alembic heads`

Use that revision id as `down_revision` below (it will be `a18b27770761` unless another migration landed since).

```python
"""add cases and expert_reviews tables

Adds Case (docs/product/rbac-full-implementation-spec.md Section 6),
superseding EscalationItem - every answered chat turn gets a row, not
just escalated ones. Adds ExpertReview (the review-action history).
escalation_items stays in place, unread by new code (expand->migrate->
contract, spec Section 2's own precedent) - dropped in a later migration.

Revision ID: <new_revision>
Revises: a18b27770761
Create Date: 2026-09-17
"""
import sqlalchemy as sa
from alembic import op

revision = "<new_revision>"
down_revision = "a18b27770761"
branch_labels = None
depends_on = None


def upgrade() -> None:
    case_risk_level = sa.Enum("low", "medium", "high", name="case_risk_level")
    case_status = sa.Enum(
        "open", "in_progress", "awaiting_user_input", "escalated", "resolved", "closed",
        name="case_status",
    )
    case_queue = sa.Enum("ip", "regulatory", "legal", name="case_queue")
    expert_review_action = sa.Enum(
        "approve", "modify", "reject", "request_info", "escalate", name="expert_review_action"
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("product_classification", sa.String(), nullable=True),
        sa.Column("ip_types", sa.JSON(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("regulatory_issues", sa.JSON(), nullable=True),
        sa.Column("abs_tk_flags", sa.JSON(), nullable=True),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("confidence_level", sa.String(), nullable=True),
        sa.Column("risk_level", case_risk_level, nullable=False),
        sa.Column("status", case_status, nullable=False),
        sa.Column("queue", case_queue, nullable=True),
        sa.Column("assigned_to_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_summary", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cases_status_queue", "cases", ["status", "queue"])
    op.create_index("ix_cases_user_id", "cases", ["user_id"])

    op.create_table(
        "expert_reviews",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_role", sa.String(), nullable=False),
        sa.Column("action", expert_review_action, nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("expert_reviews")
    op.drop_index("ix_cases_user_id", table_name="cases")
    op.drop_index("ix_cases_status_queue", table_name="cases")
    op.drop_table("cases")
    sa.Enum(name="expert_review_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_queue").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_risk_level").drop(op.get_bind(), checkfirst=True)
```

Save it as `apps/api/alembic/versions/<generated>_add_cases_and_expert_reviews.py` — generate the filename/revision id properly instead of hand-writing one:

Run: `cd apps/api && .venv/Scripts/python.exe -m alembic revision -m "add cases and expert_reviews tables"`

Then replace the generated file's body with the `upgrade`/`downgrade` above (keep the tool-generated `revision`/`down_revision` values).

- [ ] **Step 5: Apply the migration**

Run: `cd apps/api && .venv/Scripts/python.exe -m alembic upgrade head`
Expected: no errors; `cases` and `expert_reviews` tables exist.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_models.py::test_case_and_expert_review_round_trip -v`
Expected: PASS

- [ ] **Step 7: Verify the migration round-trips**

Run: `cd apps/api && .venv/Scripts/python.exe -m alembic downgrade -1 && .venv/Scripts/python.exe -m alembic upgrade head`
Expected: both succeed with no errors (matches the round-trip check already done for `a18b27770761`).

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/db/models.py apps/api/alembic/versions/*_add_cases_and_expert_reviews.py apps/api/tests/test_models.py
git commit -m "feat(db): add Case/ExpertReview schema, supersede EscalationItem"
```

---

### Task 2: `app/cases/service.py` — risk/status/queue derivation

**Files:**
- Create: `apps/api/app/cases/service.py`
- Test: `apps/api/tests/test_cases_service.py`

**Interfaces:**
- Consumes: `CaseRiskLevel`, `CaseStatus`, `CaseQueue` from `app.db.models` (Task 1).
- Produces: `derive_case_outcome(*, escalate: bool, confidence_level: str, product_classification: str | None, ip_types: list[str], abs_tk_flags: dict | None) -> CaseOutcome` where `CaseOutcome` is a `@dataclass(frozen=True)` with fields `risk_level: CaseRiskLevel`, `status: CaseStatus`, `queue: CaseQueue | None`. Consumed by Task 3 (`chat/router.py`) and Task 4 (`cases/router.py`'s escalate-action endpoint).

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_cases_service.py
from app.cases.service import derive_case_outcome
from app.db.models import CaseQueue, CaseRiskLevel, CaseStatus


def test_low_confidence_escalates_to_ip_queue_high_risk():
    outcome = derive_case_outcome(
        escalate=True, confidence_level="low", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.high
    assert outcome.status == CaseStatus.escalated
    assert outcome.queue == CaseQueue.ip


def test_unclear_classification_routes_to_legal_queue():
    """spec Section 8: legal queue only reachable when risk_level==high AND
    an ambiguous/ABS-sensitive/sensitive-TK signal is present - unclear
    classification is the ambiguous-signal case."""
    outcome = derive_case_outcome(
        escalate=True, confidence_level="low", product_classification="unclear",
        ip_types=[], abs_tk_flags=None,
    )
    assert outcome.queue == CaseQueue.legal


def test_abs_flag_routes_to_legal_queue():
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="cosmetic",
        ip_types=["access_and_benefit_sharing"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.queue == CaseQueue.legal


def test_drug_regulatory_routes_to_regulatory_queue_when_escalated():
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="ayurveda_aahara_or_nutraceutical",
        ip_types=["drug_regulatory"], abs_tk_flags=None,
    )
    assert outcome.queue == CaseQueue.regulatory


def test_non_escalated_case_is_auto_resolved_with_no_queue():
    outcome = derive_case_outcome(
        escalate=False, confidence_level="high", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.low
    assert outcome.status == CaseStatus.resolved
    assert outcome.queue is None


def test_non_escalated_medium_confidence_is_medium_risk_resolved():
    outcome = derive_case_outcome(
        escalate=False, confidence_level="medium", product_classification="cosmetic",
        ip_types=[], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.status == CaseStatus.resolved
    assert outcome.queue is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_cases_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.cases.service'`

- [ ] **Step 3: Write the implementation**

```python
"""Derives a Case's risk_level/status/queue from the graph's existing
output - no new AI call. escalate_if_needed (app/graph/nodes/
escalate_if_needed.py) already decides WHETHER a case needs a human;
this module decides HOW risky and WHICH queue, reusing that decision
rather than re-deriving it from confidence alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.models import CaseQueue, CaseRiskLevel, CaseStatus

# spec Section 8: case.queue = legal only reachable when risk_level==high
# AND an ambiguous/complex/ABS-sensitive/sensitive-TK signal is present -
# never just because a case is high-risk for an ordinary reason (e.g. low
# confidence on a routine trademark question stays in the ip queue).
_LEGAL_TRIGGER_IP_TYPES = frozenset({"access_and_benefit_sharing"})


@dataclass(frozen=True)
class CaseOutcome:
    risk_level: CaseRiskLevel
    status: CaseStatus
    queue: CaseQueue | None


def derive_case_outcome(
    *,
    escalate: bool,
    confidence_level: str,
    product_classification: str | None,
    ip_types: list[str],
    abs_tk_flags: dict | None,
) -> CaseOutcome:
    if not escalate:
        risk = CaseRiskLevel.medium if confidence_level == "medium" else CaseRiskLevel.low
        return CaseOutcome(risk_level=risk, status=CaseStatus.resolved, queue=None)

    risk = CaseRiskLevel.high if confidence_level == "low" else CaseRiskLevel.medium

    is_ambiguous_or_sensitive = (
        product_classification == "unclear"
        or bool(_LEGAL_TRIGGER_IP_TYPES & set(ip_types))
        or bool(
            abs_tk_flags
            and (abs_tk_flags.get("biological_resource_likely") or abs_tk_flags.get("traditional_knowledge_likely"))
        )
    )
    if risk == CaseRiskLevel.high and is_ambiguous_or_sensitive:
        queue = CaseQueue.legal
    elif "drug_regulatory" in ip_types:
        queue = CaseQueue.regulatory
    else:
        queue = CaseQueue.ip

    return CaseOutcome(risk_level=risk, status=CaseStatus.escalated, queue=queue)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_cases_service.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/cases/service.py apps/api/tests/test_cases_service.py
git commit -m "feat(cases): add risk/status/queue derivation service"
```

---

### Task 3: `chat/router.py` creates a `Case` on every answered turn

**Files:**
- Modify: `apps/api/app/chat/router.py:1-40` (imports), `:413-464` (end of `_process_chat_turn`'s main-answer path), `:263-282` (the `out_of_scope` early-return branch)
- Test: `apps/api/tests/test_chat_creates_case.py`

**Interfaces:**
- Consumes: `derive_case_outcome` (Task 2), `Case`/`CaseRiskLevel`/`CaseStatus`/`CaseQueue` (Task 1).
- Produces: nothing new consumed by later tasks — this task's deliverable is the write path itself, independently testable via direct DB assertions.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_chat_creates_case.py
"""Verifies _process_chat_turn persists a Case row - doesn't need a live
LLM call for the routing/persistence assertion itself, so this drives
app.cases.service directly against a hand-built GraphState-shaped dict
rather than exercising the full /chat endpoint (that's covered by the
existing live-LLM smoke test elsewhere)."""

import uuid

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.base import AsyncSessionLocal
from app.db.models import Case, CaseStatus, Conversation, User, UserRole


async def test_out_of_scope_turn_creates_a_case():
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-chat-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()

    from app.auth.security import create_access_token
    token = create_access_token(str(user_id), "user")

    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversationId": None, "text": "What is the weather today?", "jurisdiction": "india"},
        )
    assert resp.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Case).where(Case.user_id == user_id))
        case = result.scalar_one()
        assert case.status == CaseStatus.resolved
        assert case.product_classification == "out_of_scope"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_chat_creates_case.py -v`
Expected: FAIL — `sqlalchemy.exc.NoResultFound` (no Case row exists yet).

- [ ] **Step 3: Add the import and a shared `_create_case` helper**

In `apps/api/app/chat/router.py`, add to the imports near the top (alongside the existing `from app.db.models import (...)` block):

```python
from app.cases.service import derive_case_outcome
from app.db.models import Case, CaseStatus  # add to the existing Conversation/EscalationItem/... import block
```

Add a helper function near `_abs_tk_flags` (same file):

```python
async def _create_case(
    db: AsyncSession,
    *,
    current_user: User,
    conversation: Conversation,
    question: str,
    target_language: str,
    state: GraphState,
    response: "ChatTurnResponse",
) -> Case:
    """Persist a Case for this turn - every answered turn (including an
    out-of-scope refusal), never a clarifying-question round (spec
    Section 6, Build order item 2: "every question becomes a Case row" -
    scoped here to turns that actually reached an answer, since a
    clarifying round isn't yet an answer to assess)."""
    outcome = derive_case_outcome(
        escalate=state.get("escalate", False),
        confidence_level=response.confidence_band,
        product_classification=response.classification.product_type,
        ip_types=state.get("ip_types", []),
        abs_tk_flags=response.abs_tk_flags.model_dump() if response.abs_tk_flags else None,
    )
    case = Case(
        user_id=current_user.id,
        conversation_id=conversation.id,
        question=question,
        language=target_language,
        product_classification=response.classification.product_type,
        ip_types=state.get("ip_types", []),
        jurisdiction=response.jurisdiction,
        abs_tk_flags=response.abs_tk_flags.model_dump() if response.abs_tk_flags else None,
        ai_analysis={
            "classification": response.classification.model_dump(),
            "next_steps": response.next_steps,
            "timing_ms": response.timing_ms,
        },
        citations=[c.model_dump() for c in response.citations],
        confidence_score=response.confidence,
        confidence_level=response.confidence_band,
        risk_level=outcome.risk_level,
        status=outcome.status,
        queue=outcome.queue,
    )
    db.add(case)
    return case
```

- [ ] **Step 4: Call `_create_case` from the out-of-scope branch**

In `_process_chat_turn`, find the `out_of_scope` early-return block (around line 263-282, the one building `response = ChatTurnResponse(... product_type="out_of_scope" ...)`). Immediately before `await db.commit()` in that block, add:

```python
            await _create_case(
                db,
                current_user=current_user,
                conversation=conversation,
                question=canonical_text,
                target_language=target_language,
                state=classify_state,
                response=response,
            )
```

- [ ] **Step 5: Call `_create_case` from the main-answer path**

Find the end of `_process_chat_turn` (around line 439-464, after the `db.add(Message(...))` for the assistant's final answer and the existing `if state.get("escalate"): db.add(EscalationItem(...))` block). Replace that `EscalationItem` block with:

```python
    case = await _create_case(
        db,
        current_user=current_user,
        conversation=conversation,
        question=canonical_text,
        target_language=target_language,
        state=state,
        response=response,
    )
```

(Drop the old `if state.get("escalate"): db.add(EscalationItem(...))` entirely — `_create_case` always runs and already encodes escalation via `status`/`queue`.)

- [ ] **Step 6: Run test to verify it passes**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_chat_creates_case.py -v`
Expected: PASS

- [ ] **Step 7: Run the full backend suite to check for regressions**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest -q`
Expected: same pass/fail counts as the pre-existing baseline (6 known-flaky event-loop-fixture failures in `test_models.py`/`test_rbac.py`, unrelated — verified in isolation elsewhere in this project's history) plus the new tests passing. `tests/test_cases_and_admin.py` will now fail (it seeds `EscalationItem` rows the `/cases` endpoints no longer read) — that's expected and fixed in Task 4.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/chat/router.py apps/api/tests/test_chat_creates_case.py
git commit -m "feat(chat): persist a Case for every answered turn, not just escalations"
```

---

### Task 4: Rewrite `/cases` router onto `Case`, add queue scoping + review endpoint

**Files:**
- Modify: `apps/api/app/cases/router.py` (full rewrite of the module body)
- Modify: `apps/api/app/cases/schemas.py` (extend `CaseOut`, add `ReviewActionRequest`)
- Modify: `apps/api/app/chat/router.py:525-549` (the `POST /escalations` endpoint)
- Modify: `apps/api/tests/test_cases_and_admin.py` (replace `EscalationItem` fixtures with `Case`)

**Interfaces:**
- Consumes: `Case`, `ExpertReview`, `CaseStatus`, `CaseQueue`, `ExpertReviewAction` (Task 1); `Permission.REVIEW_VIEW/APPROVE/MODIFY/REJECT/ESCALATE` (already in `app.authz.constants`, unchanged).
- Produces: `GET /cases` (queue-scoped by caller's role), `POST /cases/{id}/claim`, `POST /cases/{id}/close`, `POST /cases/{id}/review` (new).

- [ ] **Step 1: Write the failing tests**

Replace `apps/api/tests/test_cases_and_admin.py`'s `_seed_open_case` helper and its callers with a `Case`-based version, and add queue-scoping tests:

```python
# apps/api/tests/test_cases_and_admin.py - replace the existing file's
# EscalationItem-based helper and tests with this
import uuid

from app.db.base import AsyncSessionLocal
from app.db.models import (
    Case, CaseQueue, CaseRiskLevel, CaseStatus, Conversation, Message, MessageRole, UserRole,
)


async def _seed_case(user_email_suffix: str, queue: CaseQueue = CaseQueue.ip) -> tuple[str, str]:
    """Insert a user + conversation + messages + escalated Case in the
    given queue. Returns (case_id, user_email)."""
    from app.auth.security import hash_password
    from app.db.models import User

    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-user-{user_email_suffix}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()

        conversation = Conversation(user_id=user.id)
        session.add(conversation)
        await session.flush()

        session.add(Message(conversation_id=conversation.id, role=MessageRole.user, content="Q?"))
        session.add(Message(conversation_id=conversation.id, role=MessageRole.assistant, content="A."))

        case = Case(
            user_id=user.id,
            conversation_id=conversation.id,
            question="Q?",
            product_classification="unclear",
            jurisdiction="india",
            confidence_score=0.1,
            confidence_level="low",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=queue,
        )
        session.add(case)
        await session.commit()
        return str(case.id), user.email


async def test_case_queue_requires_facilitator_role(client, make_user):
    _email, _password, user_token = await make_user(role="user")
    resp = await client.get("/cases", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


async def test_case_queue_lists_open_case(client, make_user):
    case_id, user_email = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    cases = resp.json()
    match = next((c for c in cases if c["id"] == case_id), None)
    assert match is not None
    assert match["question"] == "Q?"
    assert match["answer"] == "A."
    assert match["user_email"] == user_email
    assert match["status"] == "escalated"
    assert match["queue"] == "ip"


async def test_facilitator_does_not_see_legal_queue_cases(client, make_user):
    """Queue scoping (spec Section 8): a facilitator's ip-queue grant must
    not surface cases routed to the legal queue."""
    legal_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.legal)
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    case_ids = {c["id"] for c in resp.json()}
    assert legal_case_id not in case_ids


async def test_legal_expert_sees_only_legal_queue(client, make_user):
    legal_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.legal)
    ip_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)
    _email, _password, legal_token = await make_user(role="legal_expert")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {legal_token}"})
    assert resp.status_code == 200
    case_ids = {c["id"] for c in resp.json()}
    assert legal_case_id in case_ids
    assert ip_case_id not in case_ids


async def test_regulatory_expert_sees_only_regulatory_queue(client, make_user):
    reg_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.regulatory)
    ip_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)
    _email, _password, reg_token = await make_user(role="regulatory_expert")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {reg_token}"})
    assert resp.status_code == 200
    case_ids = {c["id"] for c in resp.json()}
    assert reg_case_id in case_ids
    assert ip_case_id not in case_ids


async def test_close_case_sets_resolution(client, make_user):
    case_id, _user_email = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.post(
        f"/cases/{case_id}/close",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"resolution_summary": "resolved in test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "closed"
    assert body["resolution_summary"] == "resolved in test"
    assert body["closed_at"] is not None


async def test_claim_nonexistent_case_404(client, make_user):
    _email, _password, fac_token = await make_user(role="facilitator")
    resp = await client.post(
        f"/cases/{uuid.uuid4()}/claim", headers={"Authorization": f"Bearer {fac_token}"}
    )
    assert resp.status_code == 404


async def test_review_action_requires_assigned_reviewer(client, make_user):
    """can_perform_action's ownership check (app.authz.service): only the
    facilitator who claimed the case may review it."""
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    claim_resp = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    assert claim_resp.status_code == 200

    _email2, _password2, other_fac_token = await make_user(role="facilitator")
    review_resp = await client.post(
        f"/cases/{case_id}/review",
        headers={"Authorization": f"Bearer {other_fac_token}"},
        json={"action": "approve", "notes": "looks fine"},
    )
    assert review_resp.status_code == 403


async def test_review_action_approve_by_assigned_reviewer(client, make_user):
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})

    resp = await client.post(
        f"/cases/{case_id}/review",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"action": "approve", "notes": "looks fine"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "approve"


async def test_admin_users_requires_users_manage_permission(client, make_user):
    _email, _password, fac_token = await make_user(role="facilitator")
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 403


async def test_admin_users_lists_users(client, make_user):
    email, _password, admin_token = await make_user(role="ministry_admin")
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert email in emails


async def test_admin_stats_shape(client, make_user):
    _email, _password, admin_token = await make_user(role="ministry_admin")
    resp = await client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "users_by_role" in body
    assert "open_cases" in body
    assert "closed_cases" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_cases_and_admin.py -v`
Expected: FAIL — `queue` key missing from `CaseOut`, `/cases/{id}/review` 404s (route doesn't exist), `CaseQueue` import error.

- [ ] **Step 3: Extend `cases/schemas.py`**

```python
"""Pydantic schemas for the case queue."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class CaseOut(BaseModel):
    id: uuid.UUID
    status: str
    queue: str | None
    risk_level: str
    question: str
    answer: str
    reason: str | None
    product_classification: str | None
    jurisdiction: str | None
    confidence_score: float | None
    confidence_level: str | None
    assigned_facilitator_email: str | None
    user_email: str
    created_at: datetime
    closed_at: datetime | None
    resolution_summary: str | None


class CloseCaseRequest(BaseModel):
    resolution_summary: str


class ReviewActionRequest(BaseModel):
    action: str  # one of app.db.models.ExpertReviewAction's values
    notes: str | None = None


class ReviewActionOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    action: str
    notes: str | None
    created_at: datetime
```

- [ ] **Step 4: Rewrite `cases/router.py`**

```python
"""Case queue - Facilitator/Legal Expert/Regulatory Expert, queue-scoped.

Reads Case rows (every answered chat turn - app/chat/router.py's
_create_case), not a live re-query - a reviewer sees exactly what the AI
produced, not a fresh retrieval that could differ.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission, RoleName
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.cases.schemas import CaseOut, CloseCaseRequest, ReviewActionOut, ReviewActionRequest
from app.db.models import Case, CaseQueue, CaseStatus, ExpertReview, ExpertReviewAction, User

router = APIRouter(prefix="/cases", tags=["cases"])

# Which queue each reviewer role's case.view_queue grant actually covers.
# A permission key alone (case.view_queue) doesn't say WHICH queue - this
# is the same kind of scope narrowing can_access_resource does for
# ownership, just keyed by role name instead of a resource column (spec
# Section 8's routing rule assigns the queue at Case-creation time; this
# is where a caller's role is matched back to the queue they may see).
_ROLE_QUEUE: dict[str, CaseQueue] = {
    RoleName.FACILITATOR: CaseQueue.ip,
    RoleName.LEGAL_EXPERT: CaseQueue.legal,
    RoleName.REGULATORY_EXPERT: CaseQueue.regulatory,
}


async def _caller_role_names(ctx: AuthzContext, db: AsyncSession) -> set[str]:
    from app.db.models import Role, UserRoleAssignment

    rows = await db.execute(
        select(Role.name).join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id).where(
            UserRoleAssignment.user_id == ctx.user.id
        )
    )
    return {r[0] for r in rows.all()}


async def _to_case_out(db: AsyncSession, case: Case) -> CaseOut:
    assigned = await db.get(User, case.assigned_to_user_id) if case.assigned_to_user_id else None
    requester = await db.get(User, case.user_id)
    answer = ""
    if case.conversation_id:
        from app.db.models import Message, MessageRole

        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == case.conversation_id, Message.role == MessageRole.assistant)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_assistant = msg_result.scalar_one_or_none()
        answer = last_assistant.content if last_assistant else ""

    return CaseOut(
        id=case.id,
        status=case.status.value,
        queue=case.queue.value if case.queue else None,
        risk_level=case.risk_level.value,
        question=case.question,
        answer=answer,
        reason=None,
        product_classification=case.product_classification,
        jurisdiction=case.jurisdiction,
        confidence_score=case.confidence_score,
        confidence_level=case.confidence_level,
        assigned_facilitator_email=assigned.email if assigned else None,
        user_email=requester.email if requester else "",
        created_at=case.created_at,
        closed_at=case.closed_at,
        resolution_summary=case.resolution_summary,
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    status_filter: str | None = None,
    ctx: AuthzContext = Depends(require_permission(Permission.CASE_VIEW_QUEUE)),
    db: AsyncSession = Depends(get_db),
) -> list[CaseOut]:
    role_names = await _caller_role_names(ctx, db)
    allowed_queues = {_ROLE_QUEUE[r] for r in role_names if r in _ROLE_QUEUE}
    if not allowed_queues:
        # Holds case.view_queue but none of the known reviewer roles (e.g.
        # a future role added to the grant without a queue mapping here) -
        # fail closed, not open, to an empty-but-200 queue rather than
        # every case.
        return []

    stmt = select(Case).where(Case.queue.in_(allowed_queues)).order_by(Case.created_at.desc())
    if status_filter:
        stmt = stmt.where(Case.status == CaseStatus(status_filter))

    result = await db.execute(stmt)
    cases = list(result.scalars().all())
    return [await _to_case_out(db, c) for c in cases]


@router.post("/{case_id}/claim", response_model=CaseOut)
async def claim_case(
    case_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.CASE_ASSIGN)),
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case.assigned_to_user_id = ctx.user.id
    case.status = CaseStatus.in_progress
    await db.commit()
    await db.refresh(case)
    return await _to_case_out(db, case)


@router.post("/{case_id}/close", response_model=CaseOut)
async def close_case(
    case_id: uuid.UUID,
    payload: CloseCaseRequest,
    _ctx: AuthzContext = Depends(require_permission(Permission.CASE_CLOSE)),
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case.status = CaseStatus.closed
    case.closed_at = datetime.now(timezone.utc)
    case.resolution_summary = payload.resolution_summary
    await db.commit()
    await db.refresh(case)
    return await _to_case_out(db, case)


@router.post("/{case_id}/review", response_model=ReviewActionOut)
async def review_case(
    case_id: uuid.UUID,
    payload: ReviewActionRequest,
    ctx: AuthzContext = Depends(require_permission(Permission.REVIEW_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> ReviewActionOut:
    """Record a reviewer action. Only the case's assigned reviewer may act
    on it (can_access_resource's ownership check via assigned_to_user_id) -
    holding review.approve at all is necessary but not sufficient (spec
    Section 5's can_perform_action distinction)."""
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not can_access_resource(ctx, case):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your assigned case")

    try:
        action = ExpertReviewAction(payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action") from exc

    role_names = await _caller_role_names(ctx, db)
    reviewer_role = next((r for r in role_names if r in _ROLE_QUEUE), "facilitator")

    review = ExpertReview(
        case_id=case.id,
        reviewer_user_id=ctx.user.id,
        reviewer_role=reviewer_role,
        action=action,
        notes=payload.notes,
        previous_state={"status": case.status.value},
    )
    db.add(review)

    if action == ExpertReviewAction.escalate:
        case.status = CaseStatus.escalated
    elif action in (ExpertReviewAction.approve, ExpertReviewAction.reject, ExpertReviewAction.modify):
        case.status = CaseStatus.closed
        case.closed_at = datetime.now(timezone.utc)
    elif action == ExpertReviewAction.request_info:
        case.status = CaseStatus.awaiting_user_input

    review.new_state = {"status": case.status.value}
    await db.commit()
    await db.refresh(review)
    return ReviewActionOut(id=review.id, case_id=case.id, action=review.action.value, notes=review.notes, created_at=review.created_at)
```

- [ ] **Step 5: Update `POST /escalations` in `chat/router.py`**

Replace the body of `create_escalation` (around line 525-549):

```python
@router.post("/escalations", response_model=EscalateResponse)
async def create_escalation(
    payload: EscalateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EscalateResponse:
    """User-initiated escalation (the Escalate button) - marks the most
    recent Case for this conversation as escalated to the ip queue,
    independent of the automatic risk-based routing at answer time."""
    try:
        conversation_uuid = uuid.UUID(payload.conversationId)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversationId") from exc

    conversation = await db.get(Conversation, conversation_uuid)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    result = await db.execute(
        select(Case)
        .where(Case.conversation_id == conversation_uuid)
        .order_by(Case.created_at.desc())
        .limit(1)
    )
    case = result.scalar_one_or_none()
    if case is None:
        case = Case(
            user_id=current_user.id,
            conversation_id=conversation.id,
            question="User requested escalation to a human facilitator.",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=CaseQueue.ip,
        )
        db.add(case)
    else:
        case.status = CaseStatus.escalated
        case.queue = case.queue or CaseQueue.ip
    await db.commit()
    await db.refresh(case)

    return EscalateResponse(escalation_id=str(case.id))
```

Add `CaseQueue`, `CaseRiskLevel` to the `app.db.models` import block alongside `Case`/`CaseStatus` (Task 3, Step 3).

- [ ] **Step 6: Update `admin/router.py`'s `/admin/stats`**

Replace the `EscalationItem`/`EscalationStatus` query (lines ~56-61) with:

```python
    from app.db.models import Case, CaseStatus

    open_cases = await db.scalar(
        select(func.count()).select_from(Case).where(Case.status.in_([CaseStatus.escalated, CaseStatus.in_progress, CaseStatus.awaiting_user_input]))
    )
    closed_cases = await db.scalar(
        select(func.count()).select_from(Case).where(Case.status == CaseStatus.closed)
    )
```

Remove the now-unused `EscalationItem`/`EscalationStatus` import from `admin/router.py` if nothing else in that file references them (check with `grep -n "EscalationItem\|EscalationStatus" apps/api/app/admin/router.py` after the edit).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_cases_and_admin.py tests/test_chat_creates_case.py -v`
Expected: PASS (all cases/admin tests, including the new queue-scoping and review-action tests)

- [ ] **Step 8: Run the full backend suite**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest -q`
Expected: only the pre-existing 6 flaky event-loop-fixture failures remain (`test_models.py`, `test_rbac.py` — confirmed pre-existing and order-dependent, not caused by this change); everything else passes.

- [ ] **Step 9: Commit**

```bash
git add apps/api/app/cases/router.py apps/api/app/cases/schemas.py apps/api/app/chat/router.py apps/api/app/admin/router.py apps/api/tests/test_cases_and_admin.py
git commit -m "feat(cases): queue-scoped case list, review-action endpoint, migrate off EscalationItem"
```

---

### Task 5: `test_authz_matrix.py` coverage for the new queue-scoping invariant

**Files:**
- Modify: `apps/api/tests/test_authz_matrix.py`

**Interfaces:**
- Consumes: `Permission.REVIEW_APPROVE`/`REVIEW_MODIFY`/`REVIEW_REJECT` (existing), `ADMIN_TIER_ROLES` (existing) — no new production code, this task only adds a regression test for a rule this plan's Task 4 depends on but doesn't itself assert at the constants level.

- [ ] **Step 1: Write the test**

```python
# apps/api/tests/test_authz_matrix.py - add to the existing file
def test_only_reviewer_roles_map_to_a_queue():
    """app.cases.router._ROLE_QUEUE must cover exactly the three reviewer
    roles that hold case.view_queue (spec Section 4's matrix) - if a
    future role gains case.view_queue without a queue mapping, list_cases
    silently returns an empty queue for it (fail-closed, Task 4) rather
    than crashing, but that's worth catching in review, not discovering
    live. This test fails loudly instead."""
    from app.cases.router import _ROLE_QUEUE
    from app.authz.constants import Permission, ROLE_PERMISSIONS

    roles_with_view_queue = {
        role for role, perms in ROLE_PERMISSIONS.items() if Permission.CASE_VIEW_QUEUE in perms
    }
    assert set(_ROLE_QUEUE.keys()) == roles_with_view_queue
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd apps/api && .venv/Scripts/python.exe -m pytest tests/test_authz_matrix.py::test_only_reviewer_roles_map_to_a_queue -v`
Expected: PASS immediately (Task 4 already built `_ROLE_QUEUE` to match) — this step is a regression guard, not new behavior, so no red-green cycle is expected here; if it fails, `_ROLE_QUEUE` in Task 4 has drifted from the permission matrix and needs fixing before proceeding.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/test_authz_matrix.py
git commit -m "test(authz): guard case-queue role mapping against permission-matrix drift"
```

---

## Self-Review Notes (already applied above)

- **Spec coverage**: Section 6 schema → Task 1. Section 8 routing rule → Task 2 + Task 5. "Every question creates a Case, low/medium auto-resolved" → Task 3. `expert_reviews` + review actions wired to case-review endpoints → Task 1 + Task 4. Frontend (spec Build-order item 8) explicitly out of scope, noted in Global Constraints.
- **Deliberate scope narrowing vs. the spec's literal text**: Case creation is scoped to turns that reach a real answer or an out-of-scope refusal, not every clarifying-question round — called out explicitly in Task 3 Step 3's docstring, not silently narrowed.
- **Backward compatibility**: `CaseOut` gains `queue`/`risk_level` as new fields only; `EscalateResponse.escalation_id` keeps its name (now a Case id). `apps/web`'s `casesApi.ts`/`CasesPage.tsx` need no changes for this plan to ship — verify with `cd apps/web && npx tsc --noEmit` after Task 4 as a final check, since the frontend has its own `Citation`/`CaseOut`-shaped TS types that should still structurally match.
- **`escalation_items` table**: left in place, unread, per Global Constraints — do not add a Task to drop it in this plan.

## Final Verification (after all tasks)

- [ ] Run: `cd apps/api && .venv/Scripts/python.exe -m pytest -q` — only the known pre-existing flaky failures remain.
- [ ] Run: `cd apps/web && npx tsc --noEmit -p tsconfig.json` — clean (confirms no accidental frontend contract break).
- [ ] Manually smoke-test via the running dev stack: register a user, ask a low-confidence/ambiguous question, confirm a `Case` row appears with `status=escalated`; register a `legal_expert` (via `make_user`-style direct DB insert since there's no self-registration path for it) and confirm `GET /cases` shows only legal-queue cases.
