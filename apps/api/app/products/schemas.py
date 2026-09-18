"""Pydantic schemas for the products dossier."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class IngredientIn(BaseModel):
    name: str
    quantity: str | None = None


class IngredientOut(BaseModel):
    name: str
    quantity: str | None = None


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    product_classification: str | None = None
    jurisdiction: str | None = None
    intended_use: str | None = None
    claims: str | None = None
    manufacturing_info: str | None = None
    target_market: str | None = None
    development_stage: str | None = None
    ingredients: list[IngredientIn] | None = None
    biological_resources: list[str] | None = None
    organization_id: uuid.UUID | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    product_classification: str | None = None
    jurisdiction: str | None = None
    intended_use: str | None = None
    claims: str | None = None
    manufacturing_info: str | None = None
    target_market: str | None = None
    development_stage: str | None = None
    ingredients: list[IngredientIn] | None = None
    biological_resources: list[str] | None = None
    ip_status: dict | None = None
    regulatory_status: dict | None = None
    abs_tk_status: dict | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    organization_id: uuid.UUID | None
    name: str
    description: str | None
    product_classification: str | None
    jurisdiction: str | None
    intended_use: str | None
    claims: str | None
    manufacturing_info: str | None
    target_market: str | None
    development_stage: str | None
    ingredients: list[IngredientOut] | None
    biological_resources: list[str] | None
    ip_status: dict | None
    regulatory_status: dict | None
    abs_tk_status: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
