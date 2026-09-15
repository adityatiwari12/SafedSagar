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
