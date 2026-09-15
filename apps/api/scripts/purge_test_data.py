"""Delete accumulated pytest-run data from the dev database - the test
suite runs against the real Postgres (a deliberate choice, see
docs/superpowers/plans/2026-09-15-phase2-ingestion.md), which means
users/conversations/etc. created by tests (emails ending @example.test
or @example.com) pile up over repeated runs and clutter the admin
dashboard / case queue for demos. Run this before a demo if either looks
cluttered.

Usage: python -m scripts.purge_test_data   (from apps/api, with the venv active)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, or_, select  # noqa: E402

from app.db.base import AsyncSessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    AuditLogEntry,
    Conversation,
    EscalationItem,
    Message,
    User,
)

_TEST_EMAIL_PATTERNS = ["%@example.test", "%@example.com"]


async def purge() -> None:
    async with AsyncSessionLocal() as session:
        test_user_ids_result = await session.execute(
            select(User.id).where(or_(*[User.email.like(p) for p in _TEST_EMAIL_PATTERNS]))
        )
        test_user_ids = [row[0] for row in test_user_ids_result.all()]
        if not test_user_ids:
            print("No test-pattern users found - nothing to purge.")
            return

        conversation_ids_result = await session.execute(
            select(Conversation.id).where(Conversation.user_id.in_(test_user_ids))
        )
        conversation_ids = [row[0] for row in conversation_ids_result.all()]

        await session.execute(delete(AuditLogEntry).where(AuditLogEntry.actor_user_id.in_(test_user_ids)))
        await session.execute(
            delete(EscalationItem).where(EscalationItem.assigned_facilitator_id.in_(test_user_ids))
        )
        if conversation_ids:
            await session.execute(
                delete(EscalationItem).where(EscalationItem.conversation_id.in_(conversation_ids))
            )
            await session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
            await session.execute(delete(Conversation).where(Conversation.id.in_(conversation_ids)))
        await session.execute(delete(User).where(User.id.in_(test_user_ids)))
        await session.commit()

        print(
            f"Purged {len(test_user_ids)} test user(s), {len(conversation_ids)} conversation(s), "
            "and their messages/escalations/audit entries."
        )


if __name__ == "__main__":
    asyncio.run(purge())
