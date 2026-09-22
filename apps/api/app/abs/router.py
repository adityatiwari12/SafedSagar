"""Product ABS (Access and Benefit-Sharing) assessment routes (Phase 9).
Mirrors app.compliance.router's ownership/permission pattern:
require_permission(...) at route entry, then can_access_resource(ctx,
product) -> 404 missing / 403 not yours."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abs.schemas import (
    ALLOWED_ENTITY_CATEGORY_VALUES,
    ALLOWED_ORIGIN_VALUES,
    ALLOWED_PURPOSE_VALUES,
    ALLOWED_SOURCING_VALUES,
    AbsAssessmentOut,
    AbsAssessmentUpdate,
)
from app.abs.service import attach_evidence, save_assessment
from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.db.models import AbsAssessment, AuditLogEntry, Product

router = APIRouter(tags=["abs"])


async def _get_owned_product(product_id: uuid.UUID, ctx: AuthzContext, db: AsyncSession) -> Product:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not can_access_resource(ctx, product):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")
    return product


def _to_out(assessment: AbsAssessment) -> AbsAssessmentOut:
    return AbsAssessmentOut(
        id=assessment.id,
        product_id=assessment.product_id,
        is_biological_resource=assessment.is_biological_resource,
        resource_description=assessment.resource_description,
        origin=assessment.origin.value if assessment.origin is not None else None,
        sourcing=assessment.sourcing.value if assessment.sourcing is not None else None,
        involves_traditional_knowledge=assessment.involves_traditional_knowledge,
        purpose=assessment.purpose.value if assessment.purpose is not None else None,
        user_entity_category=(
            assessment.user_entity_category.value if assessment.user_entity_category is not None else None
        ),
        preliminary_framework=assessment.preliminary_framework,
        applicable_provisions=assessment.applicable_provisions,
        next_steps=assessment.next_steps,
        status=assessment.status.value,
        updated_by_user_id=assessment.updated_by_user_id,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


def _default_out(product_id: uuid.UUID) -> AbsAssessmentOut:
    """Not-yet-started shape for a product with no ABS assessment row yet
    - the wizard should be able to GET on first load without a 404."""
    return AbsAssessmentOut(
        id=None,
        product_id=product_id,
        is_biological_resource=None,
        resource_description=None,
        origin=None,
        sourcing=None,
        involves_traditional_knowledge=None,
        purpose=None,
        user_entity_category=None,
        preliminary_framework=None,
        applicable_provisions=None,
        next_steps=None,
        status="not_started",
        updated_by_user_id=None,
        created_at=None,
        updated_at=None,
    )


def _validate_payload(payload: AbsAssessmentUpdate) -> None:
    if payload.origin is not None and payload.origin not in ALLOWED_ORIGIN_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"origin must be one of: {', '.join(sorted(ALLOWED_ORIGIN_VALUES))}",
        )
    if payload.sourcing is not None and payload.sourcing not in ALLOWED_SOURCING_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sourcing must be one of: {', '.join(sorted(ALLOWED_SOURCING_VALUES))}",
        )
    if payload.purpose is not None and payload.purpose not in ALLOWED_PURPOSE_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"purpose must be one of: {', '.join(sorted(ALLOWED_PURPOSE_VALUES))}",
        )
    if payload.user_entity_category is not None and payload.user_entity_category not in ALLOWED_ENTITY_CATEGORY_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"user_entity_category must be one of: {', '.join(sorted(ALLOWED_ENTITY_CATEGORY_VALUES))}",
        )


@router.get("/products/{product_id}/abs", response_model=AbsAssessmentOut)
async def get_product_abs_assessment(
    product_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AbsAssessmentOut:
    product = await _get_owned_product(product_id, ctx, db)

    result = await db.execute(select(AbsAssessment).where(AbsAssessment.product_id == product.id))
    assessment = result.scalars().first()
    if assessment is None:
        return _default_out(product.id)
    return _to_out(assessment)


@router.put("/products/{product_id}/abs", response_model=AbsAssessmentOut)
async def save_product_abs_assessment(
    product_id: uuid.UUID,
    payload: AbsAssessmentUpdate,
    with_evidence: bool = False,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> AbsAssessmentOut:
    product = await _get_owned_product(product_id, ctx, db)
    _validate_payload(payload)

    assessment = await save_assessment(db, product, payload.model_dump(), ctx.user)

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="abs.save",
            detail={
                "product_id": str(product.id),
                "assessment_id": str(assessment.id),
                "status": assessment.status.value,
            },
        )
    )

    if with_evidence:
        # Slow path: live embedding + retrieval, same as the compliance
        # checklist's with_evidence flag.
        await attach_evidence(db, assessment, product)
        db.add(
            AuditLogEntry(
                actor_user_id=ctx.user.id,
                action="abs.evidence",
                detail={
                    "product_id": str(product.id),
                    "assessment_id": str(assessment.id),
                    "evidence_count": len(assessment.applicable_provisions or []),
                },
            )
        )

    await db.commit()
    await db.refresh(assessment)
    return _to_out(assessment)
