"""Pydantic schemas for the /language/detect and /translate endpoints
(task Section 9)."""

from pydantic import BaseModel


class DetectRequest(BaseModel):
    text: str
    ui_language: str | None = None


class DetectResponse(BaseModel):
    detected_language: str
    confidence: float


class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str


class TranslateResponse(BaseModel):
    text: str
    translation_status: str
    needs_human_review: bool
