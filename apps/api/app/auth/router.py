"""Auth endpoints: register, login, current-user lookup."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_db
from app.auth.schemas import Token, UserCreate, UserOut
from app.auth.security import create_access_token, hash_password, verify_password
from app.db.models import Role, User, UserRole, UserRoleAssignment, VerificationStatus

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Self-register. `role` selects among the self-registerable set
    (user/facilitator/regulatory_expert - UserCreate's validator already
    rejects anything else, including admin). All self-registered roles
    activate immediately (verification_status=approved) - the pending-
    until-admin-approval gate documented in
    docs/product/rbac-architecture-and-ux-spec.md Section 2 was removed
    per explicit request (demo/hackathon context: no admin-approval loop
    to demo through). VerificationStatus/`pending` still exist in the
    schema for when that gate is reinstated later. institutional_admin/
    ministry_admin/kb_manager tiers do not exist as self-registerable
    roles at all - admin stays a single seeded-only role."""
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    role = UserRole(payload.role)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
        persona=payload.persona if role == UserRole.user else None,
        verification_status=VerificationStatus.approved,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        # The pre-check above has a race window between two concurrent
        # registrations for the same email; the unique constraint is the
        # real guard, this just keeps the response a 400 instead of 500.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        ) from exc

    # New authorization source of truth is user_roles, not the legacy
    # `role` column above (kept only for the migration window - see
    # app.db.models.UserRole's docstring). Every registration must also
    # land a UserRoleAssignment row, or the account would have zero
    # permissions under app.authz.service despite `role` looking set.
    role_row = await db.scalar(select(Role).where(Role.name == role.value))
    if role_row is None:
        # Seed data (app.authz.seed) not applied - fail loudly rather than
        # silently create a permissionless account.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role catalog not seeded - contact an administrator.",
        )
    db.add(UserRoleAssignment(user_id=user.id, role_id=role_row.id, organization_id=None))
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """OAuth2 password flow: exchange email/password for a bearer token."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = await db.scalar(select(User).where(User.email == form_data.username))
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise unauthorized

    token = create_access_token(str(user.id), user.role.value)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
