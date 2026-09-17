"""ORM models for the IP-SAKTI Sahayak backend."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    """Legacy single-role column type.

    DEPRECATED as of docs/product/rbac-full-implementation-spec.md, which
    resolves the "Open decision" this docstring used to describe. The
    live source of truth for a user's roles is now the `user_roles`
    (`UserRoleAssignment`) table, seeded from `roles`/8 values, not this
    4-value enum. This column and enum stay only for the migration's
    expand→migrate→contract window (spec Section 2): existing code paths
    that still read `User.role` keep working during the cutover, but no
    new authorization logic should be written against it - use
    `app.authz.service` instead. Removed in a follow-up migration once
    nothing reads this column.
    """

    user = "user"
    facilitator = "facilitator"
    regulatory_expert = "regulatory_expert"
    admin = "admin"


class VerificationStatus(str, enum.Enum):
    """Gates facilitator/regulatory_expert dashboard access until an
    admin approves their professional credentials. Meaningless for
    `user`/`admin` (both default to `approved` - a plain user was never
    unverified, and admin accounts are provisioned directly, never via
    self-registration)."""

    approved = "approved"
    pending = "pending"
    rejected = "rejected"


# Roles a caller may request at self-registration. Admin is never in this
# set - provisioned out-of-band only (see the ORM docstring above).
SELF_REGISTERABLE_ROLES = {UserRole.user, UserRole.facilitator, UserRole.regulatory_expert}

# NOTE: an admin-approval gate for facilitator/regulatory_expert
# (VerificationStatus.pending at registration) was designed and briefly
# implemented, then removed on explicit request for the demo/hackathon
# build - all self-registered roles now activate immediately. The
# `VerificationStatus` enum and `User.verification_status` column stay in
# the schema for when that gate is reinstated.


class MessageRole(str, enum.Enum):
    """Author role for a single conversation message."""

    user = "user"
    assistant = "assistant"


class EscalationStatus(str, enum.Enum):
    """Lifecycle status for an escalation item."""

    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class Jurisdiction(str, enum.Enum):
    """Legal jurisdiction scope for a source document."""

    india = "india"
    international = "international"


class OrganizationType(str, enum.Enum):
    """What kind of entity an Organization row represents - drives no
    permission differences by itself (an institution and a startup are
    scoped identically), just a UI/reporting label."""

    institution = "institution"
    startup = "startup"
    other = "other"


class KnowledgeVisibility(str, enum.Enum):
    """TK record visibility (docs/product/rbac-full-implementation-spec.md
    Section 6). Default is `private` everywhere it's set - never `public`
    by default, per the spec's explicit anti-extraction requirement."""

    private = "private"
    restricted = "restricted"
    public = "public"


class KnowledgeAccessRole(str, enum.Enum):
    """Which kind of grantee a `knowledge_record_access` row names, when
    it's a role-shaped grant (e.g. "any assigned facilitator on this
    record's case") rather than one specific user."""

    facilitator = "facilitator"
    legal_expert = "legal_expert"
    regulatory_expert = "regulatory_expert"


class User(Base):
    """A platform user (end user, facilitator, or admin)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=False
    )
    # Only meaningful for role=user: entrepreneur | practitioner_researcher
    # | cultivator - drives dashboard/intake framing, never permissions
    # (CLAUDE.md: these personas "differ in intake context, not
    # permissions"). Plain string, not an enum: it's profile data, not an
    # RBAC-relevant value.
    persona: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status"),
        nullable=False,
        server_default=VerificationStatus.approved.value,
    )
    jurisdiction_preference: Mapped[str | None] = mapped_column(String, nullable=True)
    # ISO 639-1 code from app.translation.languages.LANGUAGES, or NULL if
    # never set - used as the UI-language fallback when a query's detected
    # language has low confidence (task Section 2).
    preferred_language: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user"
    )
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user"
    )
    organization_memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user"
    )


class Conversation(Base):
    """A conversation session belonging to a user."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    # The conversation's active UI language - set from the first turn's
    # detected/selected language, reused as the fallback for subsequent
    # low-confidence detections in the same conversation.
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    """A single message within a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="message_role"), nullable=False
    )
    # Canonical English text - what the graph/history-folding actually see
    # (app/chat/router.py), regardless of what language the turn was in.
    content: Mapped[str] = mapped_column(String, nullable=False)
    # What was actually shown to/typed by the user: the raw user input as
    # typed, or the localized (translated) answer for an assistant turn.
    # Separate from `content` so reopening a past conversation (history
    # view) displays what the person actually saw, not the English pivot
    # text used internally for context-folding.
    display_text: Mapped[str | None] = mapped_column(String, nullable=True)
    # The full ChatTurnResponse this assistant message produced (citations,
    # classification, confidence, ...) - NULL for user messages. Lets the
    # history view re-render exactly what was shown, not just plain text.
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Turn language - the raw user text's detected language, or the
    # answer's target language for an assistant message.
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class EscalationItem(Base):
    """A conversation escalated to a human facilitator."""

    __tablename__ = "escalation_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    status: Mapped[EscalationStatus] = mapped_column(
        SAEnum(EscalationStatus, name="escalation_status"), nullable=False
    )
    assigned_facilitator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # Denormalized snapshot of the graph's output at escalation time, so a
    # facilitator/regulatory expert can review the case without re-running
    # the query - matches what the AI actually saw, not a live re-query
    # that could retrieve differently later.
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    product_classification: Mapped[str | None] = mapped_column(String, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    conversation: Mapped["Conversation"] = relationship()
    assigned_facilitator: Mapped["User | None"] = relationship()


class AuditLogEntry(Base):
    """An audit trail entry for a user action."""

    __tablename__ = "audit_log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor_user: Mapped["User | None"] = relationship()


class SourceDocument(Base):
    """A single retrievable chunk of a legal source document.

    One logical document (an Act, a treaty) has many chunk rows sharing
    the same `doc_id` - `id` is the chunk's own unique key. Document-level
    fields (title/authority/jurisdiction/...) are denormalized onto every
    chunk row so a retrieved chunk carries its full citation without a
    join; `validate_citations` (Phase 3) matches a citation's `doc_id` +
    `section_or_article` against this table.
    """

    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    authority: Mapped[str] = mapped_column(String, nullable=False)
    jurisdiction: Mapped[Jurisdiction] = mapped_column(
        SAEnum(Jurisdiction, name="doc_jurisdiction"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    section_or_article: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    last_verified_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_text: Mapped[str] = mapped_column(String, nullable=False)


# ---------------------------------------------------------------------------
# Permission engine (docs/product/rbac-full-implementation-spec.md Sections
# 2-5). `Role`/`Permission` are seed DATA (plain unique strings), not Python
# enums - the whole point of moving off the old 4-value `UserRole` enum is
# that adding a role/permission should be a seed-data row, not a Postgres
# `ALTER TYPE ... ADD VALUE` migration every time.
# ---------------------------------------------------------------------------


class Role(Base):
    """A named role (`facilitator`, `kb_manager`, ...). See
    app.authz.constants for the canonical set of role-name strings."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role")


class Permission(Base):
    """A single resource+action permission (`case.create`, `source.publish`,
    ...). `key` is what code checks (`has_permission(ctx, "case.create")`);
    `resource`/`action` are the same thing split for querying/reporting."""

    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="permission")


class RolePermission(Base):
    """Grants one Permission to one Role. The role/permission matrix in
    the spec is seeded as rows here (app/authz/seed.py), not hardcoded in
    application logic."""

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="ux_role_permission"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id"), nullable=False)

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")


class Organization(Base):
    """An institution, startup/MSME, or other entity that Cases/Products/
    ResearchProjects/etc. can be scoped to (spec Section 3)."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    org_type: Mapped[OrganizationType] = mapped_column(
        SAEnum(OrganizationType, name="organization_type"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization")


class OrganizationMember(Base):
    """Plain membership - who belongs to which Organization. A member's
    *role within* that org (institutional_admin, or just a plain user
    affiliated with it) is a separate `UserRoleAssignment` row, not a
    column here - this table only answers "is this user part of this
    org," which every org-scope check needs regardless of role."""

    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="ux_org_member"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="organization_memberships")
    organization: Mapped["Organization"] = relationship(back_populates="members")


class UserRoleAssignment(Base):
    """One (user, role[, organization]) grant - the live source of truth
    for authorization (app.authz.service), superseding the legacy
    `User.role` column (spec Section 2). `organization_id` is NULL for a
    platform-wide role grant (ministry_admin, kb_manager, legal_expert,
    facilitator, regulatory_expert, or a `user` role with no org
    affiliation) and set for an org-scoped grant (institutional_admin for
    one specific Organization).

    A nullable column can't be part of a Postgres PRIMARY KEY, so this
    uses a surrogate `id` plus two partial unique indexes (below) instead
    of a composite key - one for org-scoped rows, one for NULL-org rows -
    so "the same user can't hold the same role twice (in the same scope)"
    is still enforced at the database level, not just in application code.
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        Index(
            "ux_user_role_scoped",
            "user_id", "role_id", "organization_id",
            unique=True,
            postgresql_where="organization_id IS NOT NULL",
        ),
        Index(
            "ux_user_role_unscoped",
            "user_id", "role_id",
            unique=True,
            postgresql_where="organization_id IS NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="role_assignments")
    role: Mapped["Role"] = relationship()
    organization: Mapped["Organization | None"] = relationship()
