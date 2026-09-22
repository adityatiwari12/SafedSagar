"""Documents - secure upload/list/get/download/delete (Phase 28), the
foundation the label/advertisement analyser (Phase 11) and the researcher
workspace build on next. Mirrors app.products.router's ownership+org gate
pattern; see app.documents.storage for the filesystem backend and
app.documents.validation for upload validation."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.db.models import AuditLogEntry, Case, Document, DocumentKind, DocumentStatus, Product
from app.documents.schemas import DocumentOut
from app.documents.storage import LocalFilesystemStorage, get_storage_backend
from app.documents.validation import DocumentValidationError, extension_for_content_type, validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])


def _sanitize_content_disposition_filename(filename: str) -> str:
    """Strip CR/LF (header injection via a crafted original filename) and
    other control characters, then escape backslashes/quotes so the value
    can't break out of the quoted-string it's placed in."""
    cleaned = "".join(ch for ch in filename if ch not in ("\r", "\n") and ord(ch) >= 0x20)
    cleaned = cleaned.replace("\\", "\\\\").replace('"', '\\"').strip()
    return cleaned or "download"


async def _can_access_case(ctx: AuthzContext, case: Case) -> bool:
    """A case's own asker isn't covered by can_access_resource (Case has
    no owner_user_id column - see app.cases.router._case_message_side,
    which draws this exact same distinction), so check it explicitly in
    addition."""
    return can_access_resource(ctx, case) or case.user_id == ctx.user.id


async def _can_access_document(ctx: AuthzContext, document: Document, db: AsyncSession) -> bool:
    """Owner OR org match on the document row itself (can_access_resource's
    normal contract), OR access to whichever product/case it's attached
    to - a document attached to a product/case the caller can otherwise
    see should itself be visible."""
    if can_access_resource(ctx, document):
        return True
    if document.product_id is not None:
        product = await db.get(Product, document.product_id)
        if product is not None and can_access_resource(ctx, product):
            return True
    if document.case_id is not None:
        case = await db.get(Case, document.case_id)
        if case is not None and await _can_access_case(ctx, case):
            return True
    return False


def _to_document_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        owner_user_id=document.owner_user_id,
        organization_id=document.organization_id,
        product_id=document.product_id,
        case_id=document.case_id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        doc_kind=document.doc_kind.value,
        status=document.status.value,
        uploaded_by_user_id=document.uploaded_by_user_id,
        created_at=document.created_at,
    )


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    doc_kind: str = Form(...),
    product_id: uuid.UUID | None = Form(None),
    case_id: uuid.UUID | None = Form(None),
    organization_id: uuid.UUID | None = Form(None),
    ctx: AuthzContext = Depends(require_permission(Permission.DOCUMENT_CREATE)),
    db: AsyncSession = Depends(get_db),
    storage: LocalFilesystemStorage = Depends(get_storage_backend),
) -> Document:
    try:
        kind = DocumentKind(doc_kind)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"doc_kind must be one of: {', '.join(k.value for k in DocumentKind)}",
        ) from exc

    file_bytes = await file.read()
    try:
        validate_upload(file.filename or "", file.content_type or "", file_bytes)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Privilege-escalation guard, same pattern as app.products.router.
    # create_product: a client-supplied organization_id is never trusted
    # at face value - it must be an org the caller actually belongs to.
    if organization_id is not None and organization_id not in ctx.organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the specified organization",
        )

    if product_id is not None:
        product = await db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        if not can_access_resource(ctx, product):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    if case_id is not None:
        case = await db.get(Case, case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        if not await _can_access_case(ctx, case):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this case")

    # The storage key is always a fresh uuid4, never derived from the
    # client-supplied filename - the extension comes from the validated
    # content-type, not the filename either.
    storage_key = f"{uuid.uuid4()}{extension_for_content_type(file.content_type)}"
    storage.save(file_bytes, storage_key)

    document = Document(
        owner_user_id=ctx.user.id,
        organization_id=organization_id,
        product_id=product_id,
        case_id=case_id,
        filename=file.filename or "upload",
        content_type=file.content_type,
        size_bytes=len(file_bytes),
        storage_key=storage_key,
        doc_kind=kind,
        status=DocumentStatus.active,
        uploaded_by_user_id=ctx.user.id,
    )
    db.add(document)
    await db.flush()
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="document.create",
            detail={"document_id": str(document.id), "filename": document.filename},
        )
    )
    await db.commit()
    await db.refresh(document)
    return _to_document_out(document)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    product_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
    ctx: AuthzContext = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    conditions = [Document.owner_user_id == ctx.user.id]
    if ctx.organization_ids:
        conditions.append(Document.organization_id.in_(ctx.organization_ids))
        accessible_product_ids = select(Product.id).where(
            or_(Product.owner_user_id == ctx.user.id, Product.organization_id.in_(ctx.organization_ids))
        )
        accessible_case_ids = select(Case.id).where(
            or_(
                Case.user_id == ctx.user.id,
                Case.assigned_to_user_id == ctx.user.id,
                Case.organization_id.in_(ctx.organization_ids),
            )
        )
    else:
        accessible_product_ids = select(Product.id).where(Product.owner_user_id == ctx.user.id)
        accessible_case_ids = select(Case.id).where(
            or_(Case.user_id == ctx.user.id, Case.assigned_to_user_id == ctx.user.id)
        )
    conditions.append(Document.product_id.in_(accessible_product_ids))
    conditions.append(Document.case_id.in_(accessible_case_ids))

    stmt = select(Document).where(Document.status == DocumentStatus.active, or_(*conditions))
    if product_id is not None:
        stmt = stmt.where(Document.product_id == product_id)
    if case_id is not None:
        stmt = stmt.where(Document.case_id == case_id)
    stmt = stmt.order_by(Document.created_at.desc())

    result = await db.execute(stmt)
    return [_to_document_out(d) for d in result.scalars().all()]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    document = await db.get(Document, document_id)
    if document is None or document.status != DocumentStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not await _can_access_document(ctx, document, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your document")
    return _to_document_out(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db),
    storage: LocalFilesystemStorage = Depends(get_storage_backend),
) -> Response:
    document = await db.get(Document, document_id)
    if document is None or document.status != DocumentStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not await _can_access_document(ctx, document, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your document")

    # Never executes/interprets the bytes - served as-is with the stored
    # content-type and a forced download disposition.
    file_bytes = storage.read(document.storage_key)
    safe_name = _sanitize_content_disposition_filename(document.filename)
    return Response(
        content=file_bytes,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.DOCUMENT_DELETE)),
    db: AsyncSession = Depends(get_db),
    storage: LocalFilesystemStorage = Depends(get_storage_backend),
) -> None:
    document = await db.get(Document, document_id)
    if document is None or document.status != DocumentStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Owner-only, deliberately stricter than read (can_access_resource
    # also admits org members / attached-resource access) - mirrors
    # app.products.router.delete_product's reasoning: a teammate reading a
    # shared document is fine, destroying it is the owner's call alone.
    if document.owner_user_id != ctx.user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the document owner can delete it",
        )

    storage.delete(document.storage_key)
    document.status = DocumentStatus.deleted
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="document.delete",
            detail={"document_id": str(document.id), "filename": document.filename},
        )
    )
    await db.commit()
