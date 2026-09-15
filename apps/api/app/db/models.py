"""ORM models for the IP-SAKTI Sahayak backend."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    """RBAC roles for platform users.

    `admin` stays a single value for now (see
    docs/product/rbac-architecture-and-ux-spec.md Section 0/"Open
    decision" - splitting it into institutional_admin/ministry_admin/
    kb_manager is a breaking migration that needs frontend coordination
    first, deliberately not done in this change). `regulatory_expert` is
    new: self-registerable-as-a-request, like `facilitator`, gated by
    `verification_status`.
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

# Roles that land pending until an admin approves, rather than being
# immediately active.
ROLES_REQUIRING_VERIFICATION = {UserRole.facilitator, UserRole.regulatory_expert}


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversations: Mapped[list["Conversation"]] = relationship(
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
    content: Mapped[str] = mapped_column(String, nullable=False)
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
