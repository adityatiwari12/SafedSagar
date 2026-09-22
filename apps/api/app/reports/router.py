"""Product assessment PDF report route (`GET /products/{id}/report`).
Mirrors app.products.router / app.compliance.router / app.abs.router's
ownership+permission pattern: require_permission(PRODUCT_VIEW) at route
entry, then can_access_resource(ctx, product) -> 404 missing / 403 not
yours. Assembles the product + its linked cases/compliance/ABS and hands
them to app.reports.builder.build_product_report_pdf - this router does
no legal reasoning of its own, it only fetches rows already in Postgres.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.cases.router import _to_case_out
from app.db.models import AbsAssessment, AuditLogEntry, ComplianceItem, Product
from app.products.router import _fetch_product_cases
from app.reports.builder import CaseEntry, build_product_report_pdf

router = APIRouter(tags=["reports"])


def _sanitize_content_disposition_filename(filename: str) -> str:
    """Same defensive stripping as app.documents.router's download
    endpoint - CR/LF and other control characters stripped (header
    injection via a crafted product name), quotes/backslashes escaped so
    the value can't break out of the quoted-string it's placed in."""
    cleaned = "".join(ch for ch in filename if ch not in ("\r", "\n") and ord(ch) >= 0x20)
    cleaned = cleaned.replace("\\", "\\\\").replace('"', '\\"').strip()
    return cleaned or "product"


@router.get("/products/{product_id}/report")
async def get_product_report(
    product_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.PRODUCT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not can_access_resource(ctx, product):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    # Same case-fetch logic app.products.router.get_product_cases uses
    # (_fetch_product_cases for the query, _to_case_out for the answer -
    # the conversation/last-assistant-message lookup), not duplicated here.
    # Raw Case rows are kept alongside the CaseOut view because CaseOut has
    # no citations field and the report must render Case.citations.
    cases = await _fetch_product_cases(db, product_id)
    case_entries: list[CaseEntry] = []
    for case in cases:
        case_out = await _to_case_out(db, case)
        case_entries.append(
            CaseEntry(
                question=case_out.question,
                answer=case_out.answer,
                confidence_level=case_out.confidence_level,
                confidence_score=case_out.confidence_score,
                status=case_out.status,
                created_at=case_out.created_at,
                citations=case.citations or [],
            )
        )

    compliance_result = await db.execute(
        select(ComplianceItem).where(ComplianceItem.product_id == product_id).order_by(ComplianceItem.area)
    )
    compliance_items = list(compliance_result.scalars().all())

    abs_result = await db.execute(select(AbsAssessment).where(AbsAssessment.product_id == product_id))
    abs_assessment = abs_result.scalars().first()

    generated_at = datetime.now(timezone.utc)
    pdf_bytes = build_product_report_pdf(
        product=product,
        cases=case_entries,
        compliance=compliance_items,
        abs_assessment=abs_assessment,
        generated_by=ctx.user.email,
        generated_at=generated_at,
    )

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="report.generate",
            detail={"product_id": str(product.id)},
        )
    )
    await db.commit()

    safe_name = _sanitize_content_disposition_filename(product.name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-assessment-report.pdf"'},
    )
