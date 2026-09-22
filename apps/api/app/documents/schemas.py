"""Pydantic schemas for the documents API."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    """Metadata only - raw bytes are never embedded in a JSON response,
    only served by GET /documents/{id}/download."""

    id: uuid.UUID
    owner_user_id: uuid.UUID
    organization_id: uuid.UUID | None
    product_id: uuid.UUID | None
    case_id: uuid.UUID | None
    filename: str
    content_type: str
    size_bytes: int
    doc_kind: str
    status: str
    uploaded_by_user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
