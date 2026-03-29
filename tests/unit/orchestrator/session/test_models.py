"""Tests for mozi.orchestrator.session.models module.

This module contains unit tests for SessionMessage and SessionState.
"""

from __future__ import annotations

from datetime import datetime

from mozi.orchestrator.session.models import SessionMessage, SessionState


class TestSessionMessage:
    """Tests for SessionMessage dataclass."""

    def test_session_message_creation(self) -> None:
        """Test SessionMessage creation with required fields."""
        msg = SessionMessage(
            id="msg_001",
            role="user",
            content="Hello",
            timestamp=datetime.now(),
            tokens=10,
        )
        assert msg.id == "msg_001"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tokens == 10
        assert msg.artifacts == []

    def test_session_message_default_artifacts(self) -> None:
        """Test SessionMessage default artifacts is empty list."""
        msg = SessionMessage(
            id="msg_002",
            role="assistant",
            content="Hi there",
            timestamp=datetime.now(),
        )
        assert msg.artifacts == []

    def test_session_message_to_dict(self) -> None:
        """Test SessionMessage.to_dict returns correct dictionary."""
        now = datetime.now()
        msg = SessionMessage(
            id="msg_001",
            role="user",
            content="Hello",
            timestamp=now,
            tokens=10,
        )
        d = msg.to_dict()
        assert d["id"] == "msg_001"
        assert d["role"] == "user"
        assert d["content"] == "Hello"
        assert d["tokens"] == 10
        assert d["artifacts"] == []

    def test_session_message_from_dict(self) -> None:
        """Test SessionMessage.from_dict creates correct instance."""
        now = datetime.now()
        data = {
            "id": "msg_001",
            "role": "user",
            "content": "Hello",
            "timestamp": now.isoformat(),
            "tokens": 10,
            "artifacts": [],
        }
        msg = SessionMessage.from_dict(data)
        assert msg.id == "msg_001"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tokens == 10

    def test_session_message_from_dict_with_artifacts(self) -> None:
        """Test SessionMessage.from_dict with artifacts."""
        now = datetime.now()
        artifacts = [{"type": "code", "content": "print('hello')"}]
        data = {
            "id": "msg_002",
            "role": "assistant",
            "content": "Here is code",
            "timestamp": now.isoformat(),
            "tokens": 50,
            "artifacts": artifacts,
        }
        msg = SessionMessage.from_dict(data)
        assert msg.artifacts == artifacts


class TestSessionState:
    """Tests for SessionState enum."""

    def test_active_state_value(self) -> None:
        """Test ACTIVE state has correct value."""
        assert SessionState.ACTIVE.value == "ACTIVE"

    def test_paused_state_value(self) -> None:
        """Test PAUSED state has correct value."""
        assert SessionState.PAUSED.value == "PAUSED"

    def test_completed_state_value(self) -> None:
        """Test COMPLETED state has correct value."""
        assert SessionState.COMPLETED.value == "COMPLETED"

    def test_abandoned_state_value(self) -> None:
        """Test ABANDONED state has correct value."""
        assert SessionState.ABANDONED.value == "ABANDONED"

    def test_error_state_value(self) -> None:
        """Test ERROR state has correct value."""
        assert SessionState.ERROR.value == "ERROR"
