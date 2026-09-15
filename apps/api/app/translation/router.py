"""POST /language/detect and POST /translate (task Section 9). Standalone
endpoints for the frontend's language selector / "translate this" UI -
independent of the /chat flow, which calls TranslationService directly."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.translation.schemas import DetectRequest, DetectResponse, TranslateRequest, TranslateResponse
from app.translation.translation_service import get_translation_service

router = APIRouter(tags=["language"])


@router.post("/language/detect", response_model=DetectResponse)
async def detect_language_endpoint(
    payload: DetectRequest,
    current_user: User = Depends(get_current_user),
) -> DetectResponse:
    service = get_translation_service()
    resolution = service.resolve_incoming(payload.text, payload.ui_language)
    return DetectResponse(
        detected_language=resolution.detected_language,
        confidence=resolution.detection_confidence,
    )


@router.post("/translate", response_model=TranslateResponse)
async def translate_endpoint(
    payload: TranslateRequest,
    current_user: User = Depends(get_current_user),
) -> TranslateResponse:
    service = get_translation_service()
    outcome = service.translate_text(payload.text, payload.source_language, payload.target_language)
    return TranslateResponse(
        text=outcome.text,
        translation_status=outcome.translation_status,
        needs_human_review=outcome.needs_human_review,
    )
