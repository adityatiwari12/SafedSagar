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
