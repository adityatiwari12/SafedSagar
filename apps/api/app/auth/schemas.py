"""Pydantic schemas for the auth API."""

import uuid

from pydantic import BaseModel


class UserCreate(BaseModel):
    """Payload for self-registration. Role is always forced to 'user' server-side."""

    email: str
    password: str


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
