"""Products - ownership+org-scoped CRUD for a product/formulation dossier
(docs/product/rbac-full-implementation-spec.md Phase 3, scoped to
Products only). Mirrors app.cases.router's permission-gate + ownership-
check structure."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.cases.router import _to_case_out
from app.cases.schemas import CaseOut
from app.db.models import AbsAssessment, AuditLogEntry, Case, ComplianceItem, Document, Product
from app.graph.state import PRODUCT_CATEGORIES
from app.products.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

_ALLOWED_JURISDICTIONS = {"india", "international"}


def _validate_classification(value: str | None) -> None:
    if value is not None and value not in PRODUCT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"product_classification must be one of: {', '.join(PRODUCT_CATEGORIES)}",
        )


def _validate_jurisdiction(value: str | None) -> None:
    if value is not None and value not in _ALLOWED_JURISDICTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"jurisdiction must be one of: {', '.join(sorted(_ALLOWED_JURISDICTIONS))}",
        )


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> Product:
    _validate_classification(payload.product_classification)
    _validate_jurisdiction(payload.jurisdiction)

    # Privilege-escalation guard, same pattern as app.admin.router's
    # role-assignment endpoint: a client-supplied organization_id is never
    # trusted at face value - it must be an org the caller actually
    # belongs to.
    if payload.organization_id is not None and payload.organization_id not in ctx.organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the specified organization",
        )

    product = Product(
        owner_user_id=ctx.user.id,
        organization_id=payload.organization_id,
        name=payload.name,
        description=payload.description,
        product_classification=payload.product_classification,
        jurisdiction=payload.jurisdiction,
        intended_use=payload.intended_use,
        claims=payload.claims,
        manufacturing_info=payload.manufacturing_info,
        target_market=payload.target_market,
        development_stage=payload.development_stage,
        ingredients=[i.model_dump() for i in payload.ingredients] if payload.ingredients is not None else None,
        biological_resources=payload.biological_resources,
    )
    db.add(product)
    await db.flush()
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="product.create",
            detail={"product_id": str(product.id), "name": product.name},
        )
    )
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
async def list_products(
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    conditions = [Product.owner_user_id == ctx.user.id]
    if ctx.organization_ids:
        conditions.append(Product.organization_id.in_(ctx.organization_ids))
    stmt = select(Product).where(or_(*conditions)).order_by(Product.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not can_access_resource(ctx, product):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")
    return product


async def _fetch_product_cases(db: AsyncSession, product_id: uuid.UUID) -> list[Case]:
    """Cases (chat turns) linked to a product, most recent first. Split out
    from get_product_cases so other modules (e.g. app.reports.router's PDF
    export) can reuse the same query instead of re-deriving it."""
    result = await db.execute(
        select(Case).where(Case.product_id == product_id).order_by(Case.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{product_id}/cases", response_model=list[CaseOut])
async def get_product_cases(
    product_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> list[CaseOut]:
    """Cases (chat turns) linked to this product - feeds the product
    dossier's Assessments tab. Same ownership gate as get_product: 404 if
    the product doesn't exist, 403 if it exists but isn't the caller's."""
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not can_access_resource(ctx, product):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    cases = await _fetch_product_cases(db, product_id)
    return [await _to_case_out(db, c) for c in cases]


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not can_access_resource(ctx, product):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    updates = payload.model_dump(exclude_unset=True)
    if "product_classification" in updates:
        _validate_classification(updates["product_classification"])
    if "jurisdiction" in updates:
        _validate_jurisdiction(updates["jurisdiction"])
    if "ingredients" in updates and updates["ingredients"] is not None:
        updates["ingredients"] = [dict(i) for i in updates["ingredients"]]

    for field, value in updates.items():
        setattr(product, field, value)
    product.updated_at = datetime.now(timezone.utc)

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="product.update",
            detail={"product_id": str(product.id), "fields": sorted(updates.keys())},
        )
    )
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_DELETE)),
    db: AsyncSession = Depends(get_db),
) -> None:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # Deletion is owner-only, deliberately stricter than read/update (which
    # use can_access_resource and so admit any member of the product's
    # organization). A teammate collaborating on a shared dossier should be
    # able to edit it; destroying it is the owner's call alone.
    if product.owner_user_id != ctx.user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the product owner can delete it",
        )

    # Detach, don't cascade: a Case is the assessment/audit record of a
    # question that was actually asked and answered, and outlives the
    # product it was about. cases.product_id is nullable with no ON DELETE,
    # so without this the delete raises a ForeignKeyViolationError (500)
    # for any product that has ever been assessed.
    await db.execute(update(Case).where(Case.product_id == product_id).values(product_id=None))

    # A compliance checklist item has no meaning without its product (unlike
    # a Case, which is an audit record of a question actually asked) - so
    # cascade-delete rather than detach. Explicit DELETE, not a DB-level
    # ON DELETE CASCADE, matching this codebase's explicit-in-code style.
    await db.execute(delete(ComplianceItem).where(ComplianceItem.product_id == product_id))

    # Same reasoning as ComplianceItem above: an ABS assessment has no
    # meaning without its product, and abs_assessments.product_id is
    # NOT NULL (unlike cases.product_id) so without this the delete
    # raises a ForeignKeyViolationError (500) for any product that has
    # ever had an ABS assessment saved.
    await db.execute(delete(AbsAssessment).where(AbsAssessment.product_id == product_id))

    # Same detach-don't-cascade reasoning as Case above: a Document can
    # outlive the specific product it was originally attached to.
    await db.execute(update(Document).where(Document.product_id == product_id).values(product_id=None))

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="product.delete",
            detail={"product_id": str(product.id), "name": product.name},
        )
    )
    await db.delete(product)
    await db.commit()
