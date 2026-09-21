"""Product compliance checklist routes (Phase 10). Mirrors
app.products.router's ownership/permission pattern: require_permission(...)
at route entry, then can_access_resource(ctx, product) -> 404 missing /
403 not yours."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.compliance.schemas import (
    ALLOWED_STATUS_VALUES,
    ComplianceChecklistOut,
    ComplianceItemOut,
    ComplianceItemUpdate,
)
from app.compliance.service import attach_evidence, generate_checklist
from app.db.models import AuditLogEntry, ComplianceItem, ComplianceStatus, Product

router = APIRouter(tags=["compliance"])


async def _get_owned_product(product_id: uuid.UUID, ctx: AuthzContext, db: AsyncSession) -> Product:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not can_access_resource(ctx, product):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")
    return product


def _to_item_out(item: ComplianceItem) -> ComplianceItemOut:
    return ComplianceItemOut(
        id=item.id,
        product_id=item.product_id,
        area=item.area.value,
        status=item.status.value,
        applicability_reason=item.applicability_reason,
        notes=item.notes,
        evidence=item.evidence,
        updated_by_user_id=item.updated_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_checklist_out(items: list[ComplianceItem]) -> ComplianceChecklistOut:
    summary = {s.value: 0 for s in ComplianceStatus}
    for item in items:
        summary[item.status.value] += 1
    summary["total"] = len(items)
    return ComplianceChecklistOut(items=[_to_item_out(i) for i in items], summary=summary)


@router.post("/products/{product_id}/compliance", response_model=ComplianceChecklistOut)
async def generate_product_checklist(
    product_id: uuid.UUID,
    with_evidence: bool = False,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> ComplianceChecklistOut:
    product = await _get_owned_product(product_id, ctx, db)

    items = await generate_checklist(db, product, ctx.user)

    if with_evidence:
        # Slow path: live embedding + retrieval per item lacking evidence.
        for item in items:
            if not item.evidence:
                await attach_evidence(db, item, product)

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="compliance.generate",
            detail={
                "product_id": str(product.id),
                "with_evidence": with_evidence,
                "item_count": len(items),
            },
        )
    )
    await db.commit()
    for item in items:
        await db.refresh(item)
    return _to_checklist_out(items)


@router.get("/products/{product_id}/compliance", response_model=ComplianceChecklistOut)
async def get_product_checklist(
    product_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> ComplianceChecklistOut:
    product = await _get_owned_product(product_id, ctx, db)

    result = await db.execute(
        select(ComplianceItem).where(ComplianceItem.product_id == product.id).order_by(ComplianceItem.area)
    )
    items = list(result.scalars().all())
    return _to_checklist_out(items)


@router.patch("/products/{product_id}/compliance/{item_id}", response_model=ComplianceItemOut)
async def update_compliance_item(
    product_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ComplianceItemUpdate,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> ComplianceItemOut:
    product = await _get_owned_product(product_id, ctx, db)

    item = await db.get(ComplianceItem, item_id)
    if item is None or item.product_id != product.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance item not found")

    updates = payload.model_dump(exclude_unset=True)
    old_status = item.status.value

    if "status" in updates and updates["status"] is not None:
        if updates["status"] not in ALLOWED_STATUS_VALUES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"status must be one of: {', '.join(sorted(ALLOWED_STATUS_VALUES))}",
            )
        item.status = ComplianceStatus(updates["status"])
    if "notes" in updates:
        item.notes = updates["notes"]

    item.updated_by_user_id = ctx.user.id

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="compliance.update",
            detail={
                "product_id": str(product.id),
                "item_id": str(item.id),
                "area": item.area.value,
                "old_status": old_status,
                "new_status": item.status.value,
            },
        )
    )
    await db.commit()
    await db.refresh(item)
    return _to_item_out(item)
