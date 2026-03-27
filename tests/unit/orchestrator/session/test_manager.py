"""Tests for mozi.orchestrator.session module.

This module contains unit tests for SessionContext and SessionManager.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from mozi.core.error import MoziSessionError
from mozi.orchestrator.session import (
    ComplexityLevel,
    SessionContext,
    SessionManager,
    SessionState,
)


class TestComplexityLevel:
    """Tests for ComplexityLevel enum."""

    def test_simple_level_value(self) -> None:
        """Test SIMPLE level has correct value."""
        assert ComplexityLevel.SIMPLE.value == "SIMPLE"

    def test_medium_level_value(self) -> None:
        """Test MEDIUM level has correct value."""
        assert ComplexityLevel.MEDIUM.value == "MEDIUM"

    def test_complex_level_value(self) -> None:
        """Test COMPLEX level has correct value."""
        assert ComplexityLevel.COMPLEX.value == "COMPLEX"


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


@pytest.mark.unit
class TestSessionContextInit:
    """Tests for SessionContext initialization."""

    def test_init_with_required_fields(self) -> None:
        """Test initialization with only required fields."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_abc123",
            created_at=now,
            updated_at=now,
        )

        assert ctx.session_id == "sess_abc123"
        assert ctx.created_at == now
        assert ctx.updated_at == now
        assert ctx.complexity_score == 0
        assert ctx.complexity_level == ComplexityLevel.SIMPLE
        assert ctx.state == SessionState.ACTIVE
        assert ctx.metadata == {}
        assert ctx.messages == []
        assert ctx.task_history == []

    def test_init_with_all_fields(self) -> None:
        """Test initialization with all fields specified."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_xyz789",
            created_at=now,
            updated_at=now,
            complexity_score=55,
            complexity_level=ComplexityLevel.MEDIUM,
            state=SessionState.PAUSED,
            metadata={"user": "test_user"},
            messages=[{"role": "user", "content": "hello"}],
            task_history=[{"task_id": "task1", "description": "test"}],
        )

        assert ctx.session_id == "sess_xyz789"
        assert ctx.complexity_score == 55
        assert ctx.complexity_level == ComplexityLevel.MEDIUM
        assert ctx.state == SessionState.PAUSED
        assert ctx.metadata == {"user": "test_user"}
        assert len(ctx.messages) == 1
        assert len(ctx.task_history) == 1


@pytest.mark.unit
class TestSessionContextMethods:
    """Tests for SessionContext methods."""

    def test_to_dict(self) -> None:
        """Test to_dict returns correct dictionary."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_test",
            created_at=now,
            updated_at=now,
            complexity_score=30,
            complexity_level=ComplexityLevel.SIMPLE,
            state=SessionState.ACTIVE,
        )

        result = ctx.to_dict()

        assert result["session_id"] == "sess_test"
        assert result["complexity_score"] == 30
        assert result["complexity_level"] == "SIMPLE"
        assert result["state"] == "ACTIVE"
        assert "created_at" in result
        assert "updated_at" in result

    def test_from_dict(self) -> None:
        """Test from_dict creates correct instance."""
        now = datetime.now()
        data = {
            "session_id": "sess_from_dict",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "complexity_score": 45,
            "complexity_level": "MEDIUM",
            "state": "ACTIVE",
            "metadata": {"key": "value"},
            "messages": [],
            "task_history": [],
        }

        ctx = SessionContext.from_dict(data)

        assert ctx.session_id == "sess_from_dict"
        assert ctx.complexity_score == 45
        assert ctx.complexity_level == ComplexityLevel.MEDIUM
        assert ctx.metadata == {"key": "value"}

    def test_add_message(self) -> None:
        """Test add_message appends to messages list."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_msg",
            created_at=now,
            updated_at=now,
        )

        ctx.add_message("user", "Hello")

        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "user"
        assert ctx.messages[0]["content"] == "Hello"
        assert "timestamp" in ctx.messages[0]

    def test_add_task(self) -> None:
        """Test add_task appends to task_history list."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_task",
            created_at=now,
            updated_at=now,
        )

        ctx.add_task("task_001", "Implement feature", "PENDING")

        assert len(ctx.task_history) == 1
        assert ctx.task_history[0]["task_id"] == "task_001"
        assert ctx.task_history[0]["description"] == "Implement feature"
        assert ctx.task_history[0]["status"] == "PENDING"

    def test_update_metadata(self) -> None:
        """Test update_metadata sets value correctly."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_meta",
            created_at=now,
            updated_at=now,
        )

        ctx.update_metadata("project", "moziproject")

        assert ctx.metadata["project"] == "moziproject"

    def test_get_metadata_existing_key(self) -> None:
        """Test get_metadata returns value for existing key."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_get",
            created_at=now,
            updated_at=now,
            metadata={"existing": "value"},
        )

        result = ctx.get_metadata("existing")

        assert result == "value"

    def test_get_metadata_missing_key_with_default(self) -> None:
        """Test get_metadata returns default for missing key."""
        now = datetime.now()
        ctx = SessionContext(
            session_id="sess_default",
            created_at=now,
            updated_at=now,
        )

        result = ctx.get_metadata("missing", "default_value")

        assert result == "default_value"


@pytest.mark.unit
class TestSessionManagerInit:
    """Tests for SessionManager initialization."""

    def test_init_creates_empty_sessions(self) -> None:
        """Test initialization creates empty sessions dict."""
        manager = SessionManager()
        assert manager._sessions == {}


@pytest.mark.unit
class TestSessionManagerCreate:
    """Tests for SessionManager.create_session()."""

    @pytest.mark.asyncio
    async def test_create_session_defaults(self) -> None:
        """Test create_session with default values."""
        manager = SessionManager()

        session = await manager.create_session()

        assert session.session_id.startswith("sess_")
        assert session.complexity_score == 0
        assert session.complexity_level == ComplexityLevel.SIMPLE
        assert session.state == SessionState.ACTIVE
        assert session.metadata == {}

    @pytest.mark.asyncio
    async def test_create_session_with_complexity(self) -> None:
        """Test create_session with specified complexity."""
        manager = SessionManager()

        session = await manager.create_session(
            complexity_score=55,
            complexity_level=ComplexityLevel.MEDIUM,
        )

        assert session.complexity_score == 55
        assert session.complexity_level == ComplexityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self) -> None:
        """Test create_session with metadata."""
        manager = SessionManager()
        metadata = {"user_id": "user_123", "project": "test"}

        session = await manager.create_session(metadata=metadata)

        assert session.metadata == metadata

    @pytest.mark.asyncio
    async def test_create_session_stores_in_memory(self) -> None:
        """Test create_session stores session in memory."""
        manager = SessionManager()

        session = await manager.create_session()

        assert session.session_id in manager._sessions


@pytest.mark.unit
class TestSessionManagerGet:
    """Tests for SessionManager.get_session()."""

    @pytest.mark.asyncio
    async def test_get_existing_session(self) -> None:
        """Test get_session retrieves existing session."""
        manager = SessionManager()
        created = await manager.create_session()

        result = await manager.get_session(created.session_id)

        assert result.session_id == created.session_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_raises(self) -> None:
        """Test get_session raises for non-existent session."""
        manager = SessionManager()

        with pytest.raises(MoziSessionError) as exc_info:
            await manager.get_session("nonexistent_id")

        assert "Session not found" in str(exc_info.value.message)
        assert exc_info.value.session_id == "nonexistent_id"


@pytest.mark.unit
class TestSessionManagerUpdate:
    """Tests for SessionManager.update_session()."""

    @pytest.mark.asyncio
    async def test_update_session_success(self) -> None:
        """Test update_session updates session correctly."""
        manager = SessionManager()
        session = await manager.create_session()
        session.complexity_score = 75
        session.complexity_level = ComplexityLevel.COMPLEX

        result = await manager.update_session(session)

        assert result.complexity_score == 75
        assert result.complexity_level == ComplexityLevel.COMPLEX

    @pytest.mark.asyncio
    async def test_update_nonexistent_session_raises(self) -> None:
        """Test update_session raises for non-existent session."""
        manager = SessionManager()
        now = datetime.now()
        session = SessionContext(
            session_id="nonexistent",
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(MoziSessionError) as exc_info:
            await manager.update_session(session)

        assert "Session not found" in str(exc_info.value.message)


@pytest.mark.unit
class TestSessionManagerDelete:
    """Tests for SessionManager.delete_session()."""

    @pytest.mark.asyncio
    async def test_delete_existing_session(self) -> None:
        """Test delete_session removes session."""
        manager = SessionManager()
        session = await manager.create_session()
        session_id = session.session_id

        await manager.delete_session(session_id)

        assert session_id not in manager._sessions

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_raises(self) -> None:
        """Test delete_session raises for non-existent session."""
        manager = SessionManager()

        with pytest.raises(MoziSessionError) as exc_info:
            await manager.delete_session("nonexistent")

        assert "Session not found" in str(exc_info.value.message)


@pytest.mark.unit
class TestSessionManagerList:
    """Tests for SessionManager.list_sessions()."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self) -> None:
        """Test list_sessions returns empty list when no sessions."""
        manager = SessionManager()

        result = await manager.list_sessions()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_sessions_all(self) -> None:
        """Test list_sessions returns all sessions."""
        manager = SessionManager()
        await manager.create_session(complexity_level=ComplexityLevel.SIMPLE)
        await manager.create_session(complexity_level=ComplexityLevel.MEDIUM)

        result = await manager.list_sessions()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_state(self) -> None:
        """Test list_sessions filters by state."""
        manager = SessionManager()
        active = await manager.create_session()
        paused = await manager.create_session()
        await manager.pause_session(paused.session_id)

        result = await manager.list_sessions(state=SessionState.ACTIVE)

        assert len(result) == 1
        assert result[0].session_id == active.session_id

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_complexity(self) -> None:
        """Test list_sessions filters by complexity level."""
        manager = SessionManager()
        await manager.create_session(complexity_level=ComplexityLevel.SIMPLE)
        await manager.create_session(complexity_level=ComplexityLevel.COMPLEX)

        result = await manager.list_sessions(complexity_level=ComplexityLevel.SIMPLE)

        assert len(result) == 1
        assert result[0].complexity_level == ComplexityLevel.SIMPLE


@pytest.mark.unit
class TestSessionManagerStateTransitions:
    """Tests for session state transitions."""

    @pytest.mark.asyncio
    async def test_pause_active_session(self) -> None:
        """Test pausing an active session."""
        manager = SessionManager()
        session = await manager.create_session()

        result = await manager.pause_session(session.session_id)

        assert result.state == SessionState.PAUSED

    @pytest.mark.asyncio
    async def test_pause_non_active_session_raises(self) -> None:
        """Test pausing a non-active session raises error."""
        manager = SessionManager()
        session = await manager.create_session()
        await manager.pause_session(session.session_id)

        with pytest.raises(MoziSessionError) as exc_info:
            await manager.pause_session(session.session_id)

        assert "Cannot pause session" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_resume_paused_session(self) -> None:
        """Test resuming a paused session."""
        manager = SessionManager()
        session = await manager.create_session()
        await manager.pause_session(session.session_id)

        result = await manager.resume_session(session.session_id)

        assert result.state == SessionState.ACTIVE

    @pytest.mark.asyncio
    async def test_resume_non_paused_session_raises(self) -> None:
        """Test resuming a non-paused session raises error."""
        manager = SessionManager()
        session = await manager.create_session()

        with pytest.raises(MoziSessionError) as exc_info:
            await manager.resume_session(session.session_id)

        assert "Cannot resume session" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_complete_session(self) -> None:
        """Test completing a session."""
        manager = SessionManager()
        session = await manager.create_session()

        result = await manager.complete_session(session.session_id)

        assert result.state == SessionState.COMPLETED

    @pytest.mark.asyncio
    async def test_abandon_session(self) -> None:
        """Test abandoning a session."""
        manager = SessionManager()
        session = await manager.create_session()

        result = await manager.abandon_session(session.session_id)

        assert result.state == SessionState.ABANDONED


@pytest.mark.unit
class TestSessionManagerHelpers:
    """Tests for SessionManager helper methods."""

    @pytest.mark.asyncio
    async def test_get_active_session_ids(self) -> None:
        """Test get_active_session_ids returns correct IDs."""
        manager = SessionManager()
        active1 = await manager.create_session()
        active2 = await manager.create_session()
        paused = await manager.create_session()
        await manager.pause_session(paused.session_id)

        result = manager.get_active_session_ids()

        assert len(result) == 2
        assert active1.session_id in result
        assert active2.session_id in result
        assert paused.session_id not in result

    @pytest.mark.asyncio
    async def test_session_exists_true(self) -> None:
        """Test session_exists returns True for existing session."""
        manager = SessionManager()
        session = await manager.create_session()

        result = await manager.session_exists(session.session_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_session_exists_false(self) -> None:
        """Test session_exists returns False for non-existent session."""
        manager = SessionManager()

        result = await manager.session_exists("nonexistent")

        assert result is False


@pytest.mark.unit
class TestSessionManagerPersistence:
    """Tests for SessionManager persistence methods."""

    @pytest.mark.asyncio
    async def test_save_and_load_session(self) -> None:
        """Test save_session and load_session roundtrip."""
        manager = SessionManager()
        session = await manager.create_session()
        session.complexity_score = 60

        await manager.save_session(session)

        loaded = await manager.load_session(session.session_id)
        assert loaded.session_id == session.session_id
        assert loaded.complexity_score == 60

    @pytest.mark.asyncio
    async def test_load_nonexistent_session_raises(self) -> None:
        """Test load_session raises for non-existent session."""
        manager = SessionManager()

        with pytest.raises(MoziSessionError) as exc_info:
            await manager.load_session("nonexistent")

        assert "Session not found" in str(exc_info.value.message)


@pytest.mark.unit
class TestModuleExports:
    """Tests for module-level exports."""

    def test_session_context_importable(self) -> None:
        """Test SessionContext is importable from module."""
        from mozi.orchestrator.session import SessionContext
        assert SessionContext is not None

    def test_session_manager_importable(self) -> None:
        """Test SessionManager is importable from module."""
        from mozi.orchestrator.session import SessionManager
        assert SessionManager is not None

    def test_complexity_level_importable(self) -> None:
        """Test ComplexityLevel is importable from module."""
        from mozi.orchestrator.session import ComplexityLevel
        assert ComplexityLevel is not None

    def test_session_state_importable(self) -> None:
        """Test SessionState is importable from module."""
        from mozi.orchestrator.session import SessionState
        assert SessionState is not None
