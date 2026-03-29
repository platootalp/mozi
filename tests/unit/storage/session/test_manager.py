"""Tests for session storage manager."""

from __future__ import annotations

from datetime import datetime

import pytest

from mozi.storage.session.manager import SessionStore
from mozi.storage.session.schema import Session, SessionStatus


@pytest.mark.asyncio
async def test_create_and_get_session_by_name(tmp_path):
    """Test creating a session with a name and retrieving it by name."""
    db_path = str(tmp_path / "test.db")
    store = SessionStore(db_path)

    session = Session(
        id="sess_with_name",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=SessionStatus.ACTIVE,
        name="my-session",
    )
    await store.create(session)

    retrieved = await store.get_by_name("my-session")
    assert retrieved is not None
    assert retrieved.name == "my-session"
    assert retrieved.id == "sess_with_name"
