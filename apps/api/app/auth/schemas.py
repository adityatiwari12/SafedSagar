"""Pydantic schemas for the auth API."""

import uuid

from pydantic import BaseModel, Field, field_validator

from app.db.models import SELF_REGISTERABLE_ROLES, UserRole

_SELF_REGISTERABLE_VALUES = {r.value for r in SELF_REGISTERABLE_ROLES}
_VALID_PERSONAS = {"entrepreneur", "practitioner_researcher", "cultivator"}


class UserCreate(BaseModel):
    """Payload for self-registration.

    `role` defaults to "user" and only accepts the self-registerable set
    (user/facilitator/regulatory_expert) - admin is never acceptable here,
    checked below rather than trusted from the request. Facilitator and
    regulatory_expert requests land with verification_status=pending in
    the router, not active until an admin approves (see
    docs/product/rbac-architecture-and-ux-spec.md Section 2).
    """

    email: str
    # max_length=72 matches bcrypt's hard input limit (bcrypt>=4.1 raises
    # instead of truncating past 72 bytes) - bounding it here turns an
    # oversized password into a 422 instead of a 500 from hash_password.
    password: str = Field(min_length=8, max_length=72)
    role: str = "user"
    # Only meaningful when role="user" - entrepreneur/practitioner_researcher/cultivator.
    persona: str | None = None

    @field_validator("role")
    @classmethod
    def _reject_non_self_registerable_role(cls, v: str) -> str:
        if v not in _SELF_REGISTERABLE_VALUES:
            allowed = ", ".join(sorted(_SELF_REGISTERABLE_VALUES))
            raise ValueError(f"role must be one of: {allowed}")
        return v

    @field_validator("persona")
    @classmethod
    def _reject_unknown_persona(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_PERSONAS:
            allowed = ", ".join(sorted(_VALID_PERSONAS))
            raise ValueError(f"persona must be one of: {allowed}")
        return v


class UserOut(BaseModel):
    """Public representation of a user."""

    id: uuid.UUID
    email: str
    role: str
    persona: str | None = None
    verification_status: str
    jurisdiction_preference: str | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """OAuth2 bearer token response."""

    access_token: str
    token_type: str = "bearer"
