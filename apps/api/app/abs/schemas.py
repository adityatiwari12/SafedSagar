"""Pydantic schemas for the product ABS (Access and Benefit-Sharing)
assessment wizard (Phase 9)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.db.models import AbsAssessmentStatus, EntityCategory, ResourceOrigin, ResourcePurpose, ResourceSourcing


class AbsEvidenceOut(BaseModel):
    doc_id: str
    section_or_article: str | None = None
    title: str
    authority: str
    source_url: str | None = None


class AbsAssessmentUpdate(BaseModel):
    """Full replace of the wizard's answerable fields - a step-save, not
    a partial patch. A field left out of the request body is treated as
    not-yet-answered (None), same as one explicitly sent as null; this is
    intentionally NOT read with `exclude_unset`, unlike
    ComplianceItemUpdate's PATCH semantics."""

    is_biological_resource: bool | None = None
    resource_description: str | None = None
    origin: str | None = None
    sourcing: str | None = None
    involves_traditional_knowledge: bool | None = None
    purpose: str | None = None
    user_entity_category: str | None = None


class AbsAssessmentOut(BaseModel):
    id: uuid.UUID | None = None
    product_id: uuid.UUID
    is_biological_resource: bool | None
    resource_description: str | None
    origin: str | None
    sourcing: str | None
    involves_traditional_knowledge: bool | None
    purpose: str | None
    user_entity_category: str | None
    preliminary_framework: str | None
    applicable_provisions: list[AbsEvidenceOut] | None
    next_steps: list[str] | None
    status: str
    updated_by_user_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


ALLOWED_ORIGIN_VALUES = {v.value for v in ResourceOrigin}
ALLOWED_SOURCING_VALUES = {v.value for v in ResourceSourcing}
ALLOWED_PURPOSE_VALUES = {v.value for v in ResourcePurpose}
ALLOWED_ENTITY_CATEGORY_VALUES = {v.value for v in EntityCategory}
ALLOWED_STATUS_VALUES = {v.value for v in AbsAssessmentStatus}
