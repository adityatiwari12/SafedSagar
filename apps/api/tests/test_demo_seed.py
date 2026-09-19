"""Tests for the idempotent demo-data seed (app.demo.seed_demo, product
spec Phase 33 "Realistic data"). Uses the default (no-LLM) mode throughout
so these stay fast - --with-assessments needs a live API server + LLM and
is exercised manually, not in the test suite.
"""

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import Case, CaseStatus, Organization, Product, User, UserRoleAssignment
from app.demo.seed_demo import (
    DEMO_EMAIL_DOMAIN,
    DEMO_ORG_NAME,
    _DEMO_PRODUCTS,
    _DEMO_QUESTIONS,
    _DEMO_USERS,
    purge,
    seed,
)


async def _counts() -> dict:
    async with AsyncSessionLocal() as db:
        org_count = len(
            (await db.execute(select(Organization.id).where(Organization.name == DEMO_ORG_NAME))).all()
        )
        user_ids = [
            row[0]
            for row in (
                await db.execute(select(User.id).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}")))
            ).all()
        ]
        product_count = (
            len((await db.execute(select(Product.id).where(Product.owner_user_id.in_(user_ids)))).all())
            if user_ids
            else 0
        )
        case_count = (
            len((await db.execute(select(Case.id).where(Case.user_id.in_(user_ids)))).all())
            if user_ids
            else 0
        )
        role_assignment_count = (
            len(
                (
                    await db.execute(
                        select(UserRoleAssignment.id).where(UserRoleAssignment.user_id.in_(user_ids))
                    )
                ).all()
            )
            if user_ids
            else 0
        )
        return {
            "org": org_count,
            "users": len(user_ids),
            "products": product_count,
            "cases": case_count,
            "role_assignments": role_assignment_count,
        }


async def test_seed_creates_expected_org_users_products_and_cases():
    await purge()  # clean slate, in case a previous failed run left demo data behind
    await seed(with_assessments=False)

    counts = await _counts()
    assert counts["org"] == 1
    assert counts["users"] == len(_DEMO_USERS)
    assert counts["products"] == len(_DEMO_PRODUCTS)
    assert counts["cases"] == len(_DEMO_QUESTIONS)
    assert counts["role_assignments"] == len(_DEMO_USERS)

    async with AsyncSessionLocal() as db:
        org = await db.scalar(select(Organization).where(Organization.name == DEMO_ORG_NAME))
        assert org is not None
        assert org.name.startswith("[DEMO] ")

        for spec in _DEMO_PRODUCTS:
            product = await db.scalar(select(Product).where(Product.name == spec["name"]))
            assert product is not None
            assert product.name.startswith("[DEMO] ")
            assert product.ingredients
            assert product.intended_use

        cases = (await db.execute(select(Case).where(Case.organization_id == org.id))).scalars().all()
        assert len(cases) == len(_DEMO_QUESTIONS)
        for case in cases:
            # Hard constraint: no fabricated legal citations in the
            # default, no-LLM seed path.
            assert not case.citations
            assert case.ai_analysis["demo"] is True

        closed = [c for c in cases if c.status == CaseStatus.closed]
        assert len(closed) == 1
        assert closed[0].resolution_summary


async def test_seed_is_idempotent():
    await seed(with_assessments=False)
    first = await _counts()

    await seed(with_assessments=False)
    second = await _counts()

    assert first == second


async def test_purge_removes_everything_seed_created():
    await seed(with_assessments=False)
    assert (await _counts())["org"] == 1

    await purge()
    counts = await _counts()
    assert counts == {"org": 0, "users": 0, "products": 0, "cases": 0, "role_assignments": 0}

    # Purge again is a safe no-op, not an error.
    await purge()
