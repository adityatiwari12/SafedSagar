"""Pydantic schemas for the product compliance checklist (Phase 10)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.db.models import ComplianceStatus


class EvidenceOut(BaseModel):
    doc_id: str
    section_or_article: str | None = None
    title: str
    authority: str
    source_url: str | None = None


class ComplianceItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    area: str
    status: str
    applicability_reason: str
    notes: str | None
    evidence: list[EvidenceOut] | None
    updated_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceChecklistOut(BaseModel):
    """The checklist plus a per-status summary, so a dossier tab can render
    e.g. "3 of 8 complete" without recomputing it client-side."""

    items: list[ComplianceItemOut]
    summary: dict[str, int]


class ComplianceItemUpdate(BaseModel):
    """Only `status` and `notes` are user-editable - evidence and
    applicability are system-derived (rules.applicable_areas / retrieve+
    rerank), not something a user can set directly."""

    status: str | None = None
    notes: str | None = None


ALLOWED_STATUS_VALUES = {s.value for s in ComplianceStatus}
