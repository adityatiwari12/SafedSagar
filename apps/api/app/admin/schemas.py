"""Pydantic schemas for admin endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    persona: str | None
    verification_status: str
    created_at: datetime


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    org_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationCreate(BaseModel):
    name: str
    org_type: str = "other"


class RoleAssignmentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_name: str
    organization_id: uuid.UUID | None


class RoleAssignmentCreate(BaseModel):
    role_name: str
    # None = platform-wide grant. Only a caller with a platform-wide
    # roles.manage grant (ministry_admin) may assign a NULL-org grant;
    # an institutional_admin may only assign within an organization_id
    # they themselves have users.manage over (enforced in the route, not
    # just by this schema accepting the field).
    organization_id: uuid.UUID | None = None


class SourceSummary(BaseModel):
    """One row per doc_id (not per chunk) - the corpus as the knowledge-
    base owner actually thinks about it: one document, versioned and
    dated, not N retrieval fragments."""

    doc_id: str
    title: str
    authority: str
    jurisdiction: str
    doc_type: str
    version: str | None
    effective_date: str | None
    last_verified_date: str | None
    source_url: str | None
    chunk_count: int


class AuditLogEntryOut(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_email: str | None
    action: str
    detail: dict | None
    created_at: datetime
