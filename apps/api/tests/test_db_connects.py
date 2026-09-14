"""Smoke test to verify database connection."""

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal


@pytest.mark.asyncio
async def test_db_connects():
    """Test that the database connection is working."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1
