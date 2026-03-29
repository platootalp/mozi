"""Tests for FileSessionStorage."""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime

import pytest

from mozi.orchestrator.session.models import SessionMessage
from mozi.storage.session.file_storage import FileSessionStorage


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.mark.asyncio
async def test_append_and_load_messages(temp_dir):
    storage = FileSessionStorage(temp_dir)
    session_id = "sess_test123"

    msg1 = SessionMessage(
        id="msg_001",
        role="user",
        content="Hello",
        timestamp=datetime.now(),
        tokens=5,
    )
    await storage.append_message(session_id, msg1)

    messages = await storage.load_messages(session_id)
    assert len(messages) == 1
    assert messages[0].content == "Hello"


@pytest.mark.asyncio
async def test_overwrite_messages(temp_dir):
    storage = FileSessionStorage(temp_dir)
    session_id = "sess_test456"

    msg1 = SessionMessage(
        id="msg_001", role="user", content="Hello",
        timestamp=datetime.now(), tokens=5
    )
    msg2 = SessionMessage(
        id="msg_002", role="user", content="World",
        timestamp=datetime.now(), tokens=5
    )

    await storage.append_message(session_id, msg1)
    await storage.append_message(session_id, msg2)

    await storage.overwrite_messages(session_id, [msg1])
    messages = await storage.load_messages(session_id)
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_delete_session(temp_dir):
    storage = FileSessionStorage(temp_dir)
    session_id = "sess_delete"

    msg = SessionMessage(
        id="msg_001", role="user", content="Hello",
        timestamp=datetime.now(), tokens=5
    )
    await storage.append_message(session_id, msg)

    await storage.delete_session(session_id)
    messages = await storage.load_messages(session_id)
    assert messages == []
