"""Pydantic schemas for the auth API."""

import uuid

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Payload for self-registration. Role is always forced to 'user' server-side."""

    email: str
    # max_length=72 matches bcrypt's hard input limit (bcrypt>=4.1 raises
    # instead of truncating past 72 bytes) - bounding it here turns an
    # oversized password into a 422 instead of a 500 from hash_password.
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    """Public representation of a user."""

    id: uuid.UUID
    email: str
    role: str
    jurisdiction_preference: str | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """OAuth2 bearer token response."""

    access_token: str
    token_type: str = "bearer"
