"""Admin-only platform views."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import UserSummary
from app.auth.dependencies import get_db, require_role
from app.db.models import EscalationItem, EscalationStatus, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    _current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[UserSummary]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.get("/stats")
async def platform_stats(
    _current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    role_counts = await db.execute(select(User.role, func.count()).group_by(User.role))
    users_by_role = {role.value: count for role, count in role_counts.all()}

    open_cases = await db.scalar(
        select(func.count()).select_from(EscalationItem).where(EscalationItem.status == EscalationStatus.open)
    )
    closed_cases = await db.scalar(
        select(func.count()).select_from(EscalationItem).where(EscalationItem.status == EscalationStatus.closed)
    )

    return {
        "users_by_role": users_by_role,
        "open_cases": open_cases or 0,
        "closed_cases": closed_cases or 0,
    }
