"""Idempotent demo-data seed for IP-SAKTI Sahayak (product spec Phase 33,
"Realistic data"). Replaces empty-state screens with a small, coherent,
clearly-labelled FICTIONAL dataset (one org, six users spanning the RBAC
role catalog, three product dossiers, three assessment cases) so the
platform can be demonstrated without hand-creating everything first.

Follows app.authz.seed's shape: a plain async function doing get-or-create/
upsert work over a real AsyncSession, invocable as `python -m
app.demo.seed_demo`, safe to re-run any number of times.

Demo-marker convention (hard constraint: every seeded record must be
unambiguously identifiable as demo, both to a human in the UI and to a
query):
  - Organization.name and Product.name are prefixed "[DEMO] ".
  - Every seeded User's email is on the @demo.ipsakti.local domain - this
    is also the SAME definition --purge uses to find what to delete, so
    seeding and teardown can never disagree about what counts as demo data.
  - Every seeded Case belongs to a demo user (its user_id), and additionally
    carries {"demo": true, ...} in ai_analysis so a case reads as demo data
    without a join back to users.

Hard constraint (never invent real legal citations): default seeding
leaves Case.citations NULL and puts an explicit placeholder string in
ai_analysis instead of a fabricated answer - see _PLACEHOLDER_ANSWER.
Only --with-assessments produces citations, and only by calling the real
/chat endpoint against the real corpus (see _seed_case's with_assessments
branch) - never hand-written.

Usage:
    python -m app.demo.seed_demo                    # fast, no LLM, safe default
    python -m app.demo.seed_demo --with-assessments  # real /chat calls - SLOW (~20-40s/question), needs the API server up
    python -m app.demo.seed_demo --purge             # tear down everything this script created
"""

from __future__ import annotations

import argparse
import asyncio
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import create_access_token, hash_password
from app.authz.constants import RoleName
from app.db.base import AsyncSessionLocal
from app.db.models import (
    AuditLogEntry,
    Case,
    CaseQueue,
    CaseRiskLevel,
    CaseStatus,
    Conversation,
    EscalationItem,
    ExpertReview,
    Message,
    Organization,
    OrganizationMember,
    OrganizationType,
    Product,
    Role,
    User,
    UserRole,
    UserRoleAssignment,
    VerificationStatus,
)

API_BASE_URL = "http://127.0.0.1:8001"

DEMO_EMAIL_DOMAIN = "demo.ipsakti.local"
DEMO_ORG_NAME = "[DEMO] AyurVeda Innovations Pvt Ltd"
# Shared login for every seeded user - printed at the end of a run so a
# demo operator can actually sign in. Not a secret worth rotating: this
# script's whole purpose is a throwaway, clearly-labelled fictional
# dataset, never real user data.
DEMO_PASSWORD = "DemoPass123!"

_PLACEHOLDER_ANSWER = (
    "[DEMO] Seeded without an AI run - use --with-assessments to generate a real, cited answer."
)

# The legacy `users.role` column (still NOT NULL - see UserRole's docstring
# in app.db.models) has no slot for legal_expert/institutional_admin/
# ministry_admin/kb_manager. Mirrors tests/conftest.py's make_user fixture:
# nothing in app.authz reads this column any more, so any legacy value is
# fine for those four - `user`/`admin` are the least-surprising placeholders.
_LEGACY_ROLE_FALLBACK: dict[str, UserRole] = {
    RoleName.USER: UserRole.user,
    RoleName.FACILITATOR: UserRole.facilitator,
    RoleName.REGULATORY_EXPERT: UserRole.regulatory_expert,
    RoleName.LEGAL_EXPERT: UserRole.user,
    RoleName.MINISTRY_ADMIN: UserRole.admin,
}

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_DEMO_USERS = [
    {
        "key": "msme",
        "email": f"msme.owner@{DEMO_EMAIL_DOMAIN}",
        "role": RoleName.USER,
        "persona": "entrepreneur",
        "in_org": True,
    },
    {
        "key": "teammate",
        "email": f"teammate@{DEMO_EMAIL_DOMAIN}",
        "role": RoleName.USER,
        "persona": "practitioner_researcher",
        "in_org": True,
    },
    {
        "key": "facilitator",
        "email": f"facilitator@{DEMO_EMAIL_DOMAIN}",
        "role": RoleName.FACILITATOR,
        "persona": None,
        "in_org": False,
    },
    {
        "key": "regulatory",
        "email": f"regulatory.expert@{DEMO_EMAIL_DOMAIN}",
        "role": RoleName.REGULATORY_EXPERT,
        "persona": None,
        "in_org": False,
    },
    {
        "key": "legal",
        "email": f"legal.expert@{DEMO_EMAIL_DOMAIN}",
        "role": RoleName.LEGAL_EXPERT,
        "persona": None,
        "in_org": False,
    },
    {
        "key": "ministry",
        "email": f"ministry.admin@{DEMO_EMAIL_DOMAIN}",
        "role": RoleName.MINISTRY_ADMIN,
        "persona": None,
        "in_org": False,
    },
]

_DEMO_PRODUCTS = [
    {
        "key": "ashwacare",
        "name": "[DEMO] AshwaCare",
        "description": (
            "Standardized Ashwagandha + Brahmi capsule formulation targeting stress "
            "and sleep support."
        ),
        "product_classification": "patent_or_proprietary_medicine",
        "jurisdiction": "india",
        "intended_use": (
            "Adjunct support for stress management and sleep quality in adults; not "
            "intended to diagnose, treat, cure, or prevent any disease."
        ),
        "claims": (
            "Reduces perceived stress and improves subjective sleep quality when taken "
            "daily for 8 weeks, based on an internal pilot (n=42, not yet peer-reviewed)."
        ),
        "manufacturing_info": (
            "Contract-manufactured at a WHO-GMP certified facility in Gujarat; "
            "hydro-alcoholic extraction, standardized to 5% withanolides."
        ),
        "target_market": (
            "Urban working professionals aged 25-45, India D2C and modern-trade pharmacy "
            "chains."
        ),
        "development_stage": (
            "Pilot batch manufactured; stability testing in progress; not yet "
            "commercially launched."
        ),
        "ingredients": [
            {"name": "Withania somnifera (Ashwagandha) root extract", "quantity": "300 mg"},
            {"name": "Bacopa monnieri (Brahmi) whole-plant extract", "quantity": "150 mg"},
            {"name": "Microcrystalline cellulose (excipient)", "quantity": "q.s."},
        ],
        "biological_resources": ["Withania somnifera", "Bacopa monnieri"],
    },
    {
        "key": "jointherb",
        "name": "[DEMO] JointHerb",
        "description": (
            "Multi-herb formulation for joint mobility and comfort, combining classical "
            "Ayurvedic ingredients in a novel ratio not described in any classical text."
        ),
        "product_classification": "new_or_non_classical_drug",
        "jurisdiction": "india",
        "intended_use": (
            "Supports joint flexibility and comfort in adults with mild activity-related "
            "joint stiffness."
        ),
        "claims": (
            "Improves self-reported joint mobility scores over 12 weeks in an open-label "
            "pilot (n=30); mechanism proposed via anti-inflammatory activity of "
            "constituent herbs."
        ),
        "manufacturing_info": (
            "Decoction-based extraction, tablet form, manufactured at a licensed "
            "Ayurvedic pharmacy in Kerala under Schedule T conditions."
        ),
        "target_market": "Adults 40+ with active lifestyles; India, retail pharmacy and online.",
        "development_stage": (
            "Formulation finalized; awaiting AYUSH manufacturing license for the new "
            "(non-classical) ratio before commercial production."
        ),
        "ingredients": [
            {"name": "Boswellia serrata (Shallaki) resin extract", "quantity": "250 mg"},
            {"name": "Commiphora wightii (Guggulu) extract", "quantity": "200 mg"},
            {"name": "Zingiber officinale (Ginger) rhizome extract", "quantity": "100 mg"},
            {"name": "Curcuma longa (Turmeric) rhizome extract", "quantity": "150 mg"},
        ],
        "biological_resources": [
            "Boswellia serrata",
            "Commiphora wightii",
            "Zingiber officinale",
            "Curcuma longa",
        ],
    },
    {
        "key": "immunoveda",
        "name": "[DEMO] ImmunoVeda",
        "description": (
            "Ready-to-mix immunity supplement powder blending classical Ayurvedic "
            "immunity herbs with Vitamin C, positioned as an Ayurveda Aahara product."
        ),
        "product_classification": "ayurveda_aahara_or_nutraceutical",
        "jurisdiction": "india",
        "intended_use": (
            "Daily dietary supplement intended to support general immune function as "
            "part of a balanced diet."
        ),
        "claims": (
            "Contains traditionally recognized immunomodulatory herbs; no disease-specific "
            "claims made on packaging, per FSSAI Ayurveda Aahara guidance."
        ),
        "manufacturing_info": (
            "Spray-dried herbal extract blend, manufactured at an FSSAI-licensed food "
            "facility in Maharashtra."
        ),
        "target_market": (
            "Health-conscious households, India, e-commerce and modern trade; family "
            "pack format."
        ),
        "development_stage": (
            "Formulation and labeling drafted; FSSAI product approval and Ayurveda Aahara "
            "category listing not yet filed."
        ),
        "ingredients": [
            {"name": "Tinospora cordifolia (Giloy) stem extract", "quantity": "200 mg"},
            {"name": "Emblica officinalis (Amla) fruit extract", "quantity": "500 mg"},
            {"name": "Ocimum sanctum (Tulsi) leaf extract", "quantity": "150 mg"},
            {"name": "Vitamin C (ascorbic acid)", "quantity": "40 mg"},
        ],
        "biological_resources": ["Tinospora cordifolia", "Emblica officinalis", "Ocimum sanctum"],
    },
]

# One question per product. Kept 1:1 with a product so "does a demo Case
# for this product already exist" is a sufficient idempotency check on its
# own (see _seed_case) - no need for a second key.
_DEMO_QUESTIONS = [
    {
        "product_key": "ashwacare",
        "question": "Can I patent a new Ashwagandha-based formulation for stress relief?",
        "ip_types": ["patent"],
        "jurisdiction": "india",
        "risk_level": CaseRiskLevel.medium,
        "status": CaseStatus.open,
        "queue": CaseQueue.ip,
    },
    {
        "product_key": "immunoveda",
        "question": "What FSSAI rules apply to marketing an Ayurveda Aahara immunity supplement?",
        "ip_types": ["drug_regulatory"],
        "jurisdiction": "india",
        "risk_level": CaseRiskLevel.medium,
        "status": CaseStatus.open,
        "queue": CaseQueue.regulatory,
    },
    {
        "product_key": "jointherb",
        "question": "What ABS obligations apply if we commercially use Indian medicinal plants?",
        "ip_types": ["access_and_benefit_sharing"],
        "jurisdiction": "india",
        "risk_level": CaseRiskLevel.high,
        "status": CaseStatus.closed,
        "queue": CaseQueue.legal,
        # A legal expert's closing note, not a fabricated legal citation -
        # no statute/section numbers here, on purpose (hard constraint #2).
        "resolution_summary": (
            "[DEMO] Legal expert reviewed and closed this case: advised the applicant "
            "that NBA/ABS approval is likely required before commercial use of the "
            "sourced medicinal plants, and to re-run this question with "
            "--with-assessments for a corpus-grounded citation before filing."
        ),
    },
]


# ---------------------------------------------------------------------------
# Seed helpers - each is get-or-create/upsert, never insert-unconditionally.
# ---------------------------------------------------------------------------


async def _get_or_create_org(db: AsyncSession) -> tuple[Organization, bool]:
    org = await db.scalar(select(Organization).where(Organization.name == DEMO_ORG_NAME))
    if org is not None:
        org.org_type = OrganizationType.startup
        return org, False

    org = Organization(name=DEMO_ORG_NAME, org_type=OrganizationType.startup)
    db.add(org)
    await db.flush()
    return org, True


async def _get_or_create_user(
    db: AsyncSession, spec: dict, org_id: uuid.UUID
) -> tuple[User, bool]:
    user = await db.scalar(select(User).where(User.email == spec["email"]))
    created = False
    if user is None:
        user = User(
            email=spec["email"],
            hashed_password=hash_password(DEMO_PASSWORD),
            role=_LEGACY_ROLE_FALLBACK[spec["role"]],
            persona=spec["persona"],
            verification_status=VerificationStatus.approved,
        )
        db.add(user)
        await db.flush()
        created = True

    role_row = await db.scalar(select(Role).where(Role.name == spec["role"]))
    assert role_row is not None, f"role {spec['role']!r} not seeded - run `python -m app.authz.seed` first"

    assignment_org_id = org_id if spec["in_org"] else None
    conditions = [
        UserRoleAssignment.user_id == user.id,
        UserRoleAssignment.role_id == role_row.id,
    ]
    conditions.append(
        UserRoleAssignment.organization_id == assignment_org_id
        if assignment_org_id is not None
        else UserRoleAssignment.organization_id.is_(None)
    )
    existing_assignment = await db.scalar(select(UserRoleAssignment).where(*conditions))
    if existing_assignment is None:
        db.add(
            UserRoleAssignment(user_id=user.id, role_id=role_row.id, organization_id=assignment_org_id)
        )

    if spec["in_org"]:
        existing_member = await db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.organization_id == org_id,
            )
        )
        if existing_member is None:
            db.add(OrganizationMember(user_id=user.id, organization_id=org_id))

    return user, created


async def _get_or_create_product(
    db: AsyncSession, spec: dict, owner_id: uuid.UUID, org_id: uuid.UUID
) -> tuple[Product, bool]:
    product = await db.scalar(
        select(Product).where(Product.owner_user_id == owner_id, Product.name == spec["name"])
    )
    fields = {
        "organization_id": org_id,
        "description": spec["description"],
        "product_classification": spec["product_classification"],
        "jurisdiction": spec["jurisdiction"],
        "intended_use": spec["intended_use"],
        "claims": spec["claims"],
        "manufacturing_info": spec["manufacturing_info"],
        "target_market": spec["target_market"],
        "development_stage": spec["development_stage"],
        "ingredients": spec["ingredients"],
        "biological_resources": spec["biological_resources"],
    }
    if product is None:
        product = Product(owner_user_id=owner_id, name=spec["name"], **fields)
        db.add(product)
        await db.flush()
        return product, True

    for field, value in fields.items():
        setattr(product, field, value)
    return product, False


async def _seed_case(
    db: AsyncSession,
    http_client: httpx.AsyncClient | None,
    spec: dict,
    *,
    msme_user: User,
    product: Product,
    token: str | None,
    with_assessments: bool,
) -> tuple[Case, str]:
    """Get-or-create the one Case for this product. Each demo product maps
    to exactly one demo question, so "does a Case linking this product to
    the msme user already exist" is idempotency enough - no second key
    needed.
    """
    existing = await db.scalar(
        select(Case).where(Case.product_id == product.id, Case.user_id == msme_user.id)
    )

    if not with_assessments:
        if existing is not None:
            return existing, "unchanged (already seeded)"
        case = Case(
            user_id=msme_user.id,
            organization_id=product.organization_id,
            product_id=product.id,
            question=spec["question"],
            language="en",
            ip_types=spec["ip_types"],
            jurisdiction=spec["jurisdiction"],
            ai_analysis={"demo": True, "answer": _PLACEHOLDER_ANSWER, "next_steps": []},
            citations=None,
            confidence_score=None,
            confidence_level=None,
            risk_level=spec["risk_level"],
            status=spec["status"],
            queue=spec["queue"],
            resolution_summary=spec.get("resolution_summary"),
            closed_at=datetime.now(timezone.utc) if spec["status"] == CaseStatus.closed else None,
        )
        db.add(case)
        await db.flush()
        return case, "created (placeholder, no citations)"

    # --with-assessments: drive the real /chat pipeline so citations are
    # genuinely corpus-grounded - never hand-written (hard constraint #2).
    # Gate on the with_assessments marker, not on "has citations" - a real
    # pipeline run can legitimately come back with zero citations (an
    # honest abstention), and that must still count as "already seeded"
    # or a re-run would hit the LLM again on every invocation.
    if (
        existing is not None
        and isinstance(existing.ai_analysis, dict)
        and existing.ai_analysis.get("with_assessments")
    ):
        return existing, "unchanged (already ran the real pipeline)"

    assert http_client is not None and token is not None
    resp = await http_client.post(
        f"{API_BASE_URL}/chat",
        json={
            "conversationId": None,
            "text": spec["question"],
            "jurisdiction": spec["jurisdiction"],
            "productId": str(product.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    conversation_id = resp.json()["conversationId"]

    new_case = await db.scalar(
        select(Case)
        .where(Case.conversation_id == uuid.UUID(conversation_id))
        .order_by(Case.created_at.desc())
    )
    if new_case is None:
        raise RuntimeError(
            f"POST /chat succeeded but no Case was created for conversation {conversation_id}"
        )

    ai_analysis = dict(new_case.ai_analysis or {})
    ai_analysis["demo"] = True
    ai_analysis["with_assessments"] = True
    new_case.ai_analysis = ai_analysis

    if existing is not None and existing.id != new_case.id:
        # Supersede the earlier placeholder - keep exactly one demo Case
        # per demo product.
        await db.delete(existing)

    await db.flush()
    citation_count = len(new_case.citations or [])
    return new_case, f"seeded via real /chat call ({citation_count} citation(s))"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def seed(*, with_assessments: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        org, org_created = await _get_or_create_org(db)
        await db.flush()
        print(f"{'created' if org_created else 'exists '} organization {org.name} ({org.id})")

        users: dict[str, User] = {}
        for spec in _DEMO_USERS:
            user, created = await _get_or_create_user(db, spec, org.id)
            users[spec["key"]] = user
            print(f"{'created' if created else 'exists '} user {spec['email']} ({spec['role']})")

        if org.created_by_user_id is None:
            org.created_by_user_id = users["msme"].id

        await db.flush()

        msme = users["msme"]
        products: dict[str, Product] = {}
        for spec in _DEMO_PRODUCTS:
            product, created = await _get_or_create_product(db, spec, msme.id, org.id)
            products[spec["key"]] = product
            print(f"{'created' if created else 'exists '} product {spec['name']}")

        await db.commit()

        if with_assessments:
            print(
                f"\n--with-assessments: driving the real /chat pipeline against {API_BASE_URL} "
                "for each demo question. This calls the actual LLM + retrieval pipeline and "
                "typically takes ~20-40s PER QUESTION (3 questions here) - be patient.\n"
            )
            token = create_access_token(str(msme.id), msme.role.value)
            async with httpx.AsyncClient(timeout=180.0) as http_client:
                for spec in _DEMO_QUESTIONS:
                    product = products[spec["product_key"]]
                    case, note = await _seed_case(
                        db,
                        http_client,
                        spec,
                        msme_user=msme,
                        product=product,
                        token=token,
                        with_assessments=True,
                    )
                    await db.commit()
                    print(f"  case for {product.name}: {note} (case_id={case.id})")
        else:
            for spec in _DEMO_QUESTIONS:
                product = products[spec["product_key"]]
                case, note = await _seed_case(
                    db,
                    None,
                    spec,
                    msme_user=msme,
                    product=product,
                    token=None,
                    with_assessments=False,
                )
                print(f"{'created' if 'created' in note else 'exists '} case for {product.name}: {note}")
            await db.commit()

        print(f"\nDemo organization: {org.name}")
        print(f"Demo login (main):  {msme.email} / {DEMO_PASSWORD}")
        print(f"All seeded users share the password: {DEMO_PASSWORD}")
        print("Teardown: python -m app.demo.seed_demo --purge")


async def purge() -> None:
    async with AsyncSessionLocal() as db:
        demo_user_ids = [
            row[0]
            for row in (
                await db.execute(select(User.id).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}")))
            ).all()
        ]
        if not demo_user_ids:
            print("No demo users found - nothing to purge.")
            return

        org = await db.scalar(select(Organization).where(Organization.name == DEMO_ORG_NAME))

        case_ids = [
            row[0]
            for row in (await db.execute(select(Case.id).where(Case.user_id.in_(demo_user_ids)))).all()
        ]
        conversation_ids = [
            row[0]
            for row in (
                await db.execute(select(Conversation.id).where(Conversation.user_id.in_(demo_user_ids)))
            ).all()
        ]

        # Detach, don't cascade for audit history - same precedent as
        # delete_product/delete_conversation: an audit entry outlives the
        # actor it's about.
        await db.execute(
            update(AuditLogEntry)
            .where(AuditLogEntry.actor_user_id.in_(demo_user_ids))
            .values(actor_user_id=None)
        )

        if case_ids:
            await db.execute(delete(ExpertReview).where(ExpertReview.case_id.in_(case_ids)))
            await db.execute(delete(Case).where(Case.id.in_(case_ids)))

        if conversation_ids:
            await db.execute(delete(EscalationItem).where(EscalationItem.conversation_id.in_(conversation_ids)))
            await db.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
            await db.execute(delete(Conversation).where(Conversation.id.in_(conversation_ids)))

        await db.execute(delete(Product).where(Product.owner_user_id.in_(demo_user_ids)))
        await db.execute(delete(OrganizationMember).where(OrganizationMember.user_id.in_(demo_user_ids)))
        await db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id.in_(demo_user_ids)))

        if org is not None:
            org.created_by_user_id = None
            await db.flush()

        await db.execute(delete(User).where(User.id.in_(demo_user_ids)))

        if org is not None:
            await db.delete(org)

        await db.commit()
        print(
            f"Purged {len(demo_user_ids)} demo users, {len(case_ids)} cases, "
            f"{len(conversation_ids)} conversations"
            f"{', and the demo organization' if org is not None else ''}."
        )


async def _async_main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-assessments",
        action="store_true",
        help=(
            "Drive the real /chat pipeline for each demo question instead of leaving "
            f"placeholders. Requires the API server running at {API_BASE_URL}. Slow "
            "(~20-40s per question)."
        ),
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Remove everything this script created (matched by the demo-marker convention).",
    )
    args = parser.parse_args()

    if args.purge:
        await purge()
        return

    await seed(with_assessments=args.with_assessments)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
