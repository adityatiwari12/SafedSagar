"""Seed fixed demo accounts, one per role, for live-demo quick login.

Idempotent: re-running updates the password/fields on existing rows
rather than erroring on duplicate email, so this is safe to run again
after wiping a dev database.

Usage: python -m scripts.seed_demo_users   (from apps/api, with the venv active)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.auth.security import hash_password  # noqa: E402
from app.db.base import AsyncSessionLocal  # noqa: E402
from app.db.models import User, UserRole, VerificationStatus  # noqa: E402

DEMO_PASSWORD = "DemoPass123!"

DEMO_USERS = [
    dict(
        email="demo-user@ipsakti.demo",
        role=UserRole.user,
        persona="entrepreneur",
        verification_status=VerificationStatus.approved,
    ),
    dict(
        email="demo-facilitator@ipsakti.demo",
        role=UserRole.facilitator,
        persona=None,
        verification_status=VerificationStatus.approved,
    ),
    dict(
        email="demo-regulatory-expert@ipsakti.demo",
        role=UserRole.regulatory_expert,
        persona=None,
        verification_status=VerificationStatus.approved,
    ),
    dict(
        email="demo-admin@ipsakti.demo",
        role=UserRole.admin,
        persona=None,
        verification_status=VerificationStatus.approved,
    ),
]


async def seed() -> None:
    hashed = hash_password(DEMO_PASSWORD)
    async with AsyncSessionLocal() as session:
        for spec in DEMO_USERS:
            existing = await session.scalar(select(User).where(User.email == spec["email"]))
            if existing is not None:
                existing.hashed_password = hashed
                existing.role = spec["role"]
                existing.persona = spec["persona"]
                existing.verification_status = spec["verification_status"]
                print(f"[update] {spec['email']} ({spec['role'].value})")
            else:
                session.add(
                    User(
                        email=spec["email"],
                        hashed_password=hashed,
                        role=spec["role"],
                        persona=spec["persona"],
                        verification_status=spec["verification_status"],
                    )
                )
                print(f"[create] {spec['email']} ({spec['role'].value})")
        await session.commit()

    print(f"\nDemo password for all accounts: {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
