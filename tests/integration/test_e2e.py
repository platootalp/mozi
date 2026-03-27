"""End-to-end integration tests for Mozi AI Coding Agent.

This module provides end-to-end integration tests covering:
- Full pipeline: intent → complexity → router → agent → orchestrator
- CLI invocation: mozi --help, mozi [task]
- Session create/get/update cycle

Tests use @pytest.mark.integration marker and mock external dependencies.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.cli.commands import (
    CLIError,
    OrchestratorFactory,
    delete_session,
    execute_task,
    execute_task_with_retry,
    get_session,
)
from mozi.infrastructure.model.adapter import (
    ModelResponse,
)
from mozi.orchestrator.core.complexity import (
    ComplexityLevel as ComplexityLevelEnum,
)
from mozi.orchestrator.core.intent import (
    IntentScope,
    IntentType,
    recognize_intent,
)
from mozi.orchestrator.core.router import (
    RoutingStrategy,
    TaskRouter,
)
from mozi.orchestrator.orchestrator import (
    MainOrchestrator,
    OrchestratorConfig,
)
from mozi.orchestrator.session.context import (
    ComplexityLevel as SessionComplexityLevel,
)
from mozi.orchestrator.session.context import (
    SessionState,
)
from mozi.orchestrator.session.manager import SessionManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_model_adapter() -> MagicMock:
    """Create a mock model adapter that returns a simple response.

    Returns
    -------
    MagicMock
        Mock adapter with chat method returning a simple final response.
    """
    adapter = MagicMock()
    mock_response = ModelResponse(
        content="<final>\nTask completed successfully.\n</final>",
        model="test-model",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        stop_reason="end_turn",
    )
    adapter.chat = AsyncMock(return_value=mock_response)
    adapter.complete = AsyncMock(return_value=mock_response)
    return adapter


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Create a mock tool registry with no tools.

    Returns
    -------
    MagicMock
        Mock registry with empty tool list.
    """
    registry = MagicMock()
    registry.list_tools = MagicMock(return_value=[])
    registry.execute = AsyncMock()
    return registry


@pytest.fixture
def session_manager() -> SessionManager:
    """Create a fresh session manager instance.

    Returns
    -------
    SessionManager
        New session manager for testing.
    """
    return SessionManager()


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create an orchestrator configuration for testing.

    Returns
    -------
    OrchestratorConfig
        Configuration with reduced iterations for faster tests.
    """
    return OrchestratorConfig(
        max_fastpath_iterations=3,
        max_enhanced_iterations=5,
        max_orchestrated_iterations=10,
        enable_monitoring=True,
        default_temperature=0.7,
        default_max_tokens=100,
    )


@pytest.fixture
def orchestrator(
    mock_model_adapter: MagicMock,
    mock_tool_registry: MagicMock,
    session_manager: SessionManager,
    orchestrator_config: OrchestratorConfig,
) -> MainOrchestrator:
    """Create an orchestrator instance with mocked dependencies.

    Parameters
    ----------
    mock_model_adapter : MagicMock
        Mock model adapter.
    mock_tool_registry : MagicMock
        Mock tool registry.
    session_manager : SessionManager
        Session manager instance.
    orchestrator_config : OrchestratorConfig
        Orchestrator configuration.

    Returns
    -------
    MainOrchestrator
        Orchestrator configured for testing.
    """
    return MainOrchestrator(
        model_adapter=mock_model_adapter,
        tool_registry=mock_tool_registry,
        session_manager=session_manager,
        config=orchestrator_config,
    )


@pytest.fixture(autouse=True)
def reset_orchestrator_factory() -> Generator[None, None, None]:
    """Reset the OrchestratorFactory singleton after each test.

    This ensures tests don't interfere with each other through
    the shared orchestrator instance.
    """
    yield
    OrchestratorFactory.reset()


# =============================================================================
# Intent Recognition Integration Tests
# =============================================================================


class TestIntentRecognitionIntegration:
    """Integration tests for intent recognition within the pipeline."""

    def test_recognize_intent_from_simple_task(self) -> None:
        """Test intent recognition for a simple file read task."""
        result = recognize_intent("read the main.py file")

        assert result is not None
        assert result.task_type == IntentType.CODE_READ
        assert result.scope == IntentScope.FILE
        assert result.confidence > 0
        assert "read" in result.keywords or "file" in result.keywords

    def test_recognize_intent_from_edit_task(self) -> None:
        """Test intent recognition for an edit task."""
        result = recognize_intent("edit the config.json file")

        assert result is not None
        assert result.task_type == IntentType.CODE_EDIT
        assert result.scope == IntentScope.FILE
        assert "edit" in result.keywords

    def test_recognize_intent_from_analysis_task(self) -> None:
        """Test intent recognition for an analysis task."""
        result = recognize_intent("analyze the entire codebase")

        assert result is not None
        assert result.task_type == IntentType.ANALYSIS
        assert result.scope == IntentScope.PROJECT
        assert result.confidence > 0

    def test_recognize_intent_from_bash_task(self) -> None:
        """Test intent recognition for a bash command task."""
        result = recognize_intent("run npm install")

        assert result is not None
        assert result.task_type == IntentType.BASH
        assert "run" in result.keywords or "npm" in result.keywords


# =============================================================================
# Router Integration Tests
# =============================================================================


class TestRouterIntegration:
    """Integration tests for task router within the pipeline."""

    def test_router_routes_simple_task_to_fastpath(self) -> None:
        """Test that simple tasks are routed to FASTPATH."""
        router = TaskRouter()
        result = router.route("read the main.py file")

        assert result is not None
        assert result.strategy == RoutingStrategy.FASTPATH
        assert result.complexity.level == ComplexityLevelEnum.SIMPLE
        assert result.intent is not None

    def test_router_routes_complex_task_to_enhanced(self) -> None:
        """Test that medium complexity tasks are routed to ENHANCED."""
        router = TaskRouter()
        result = router.route(
            "refactor multiple modules in the project",
            file_count=15,
            operation_types=["read", "edit", "write"],
        )

        assert result is not None
        assert result.strategy == RoutingStrategy.ENHANCED
        assert result.complexity.level == ComplexityLevelEnum.MEDIUM

    def test_router_routes_very_complex_task_to_orchestrated(self) -> None:
        """Test that complex tasks are routed to ORCHESTRATED."""
        router = TaskRouter()
        # Use high-weight operations and many files to ensure COMPLEX routing
        result = router.route(
            "analyze the entire repository and create a comprehensive report",
            file_count=100,
            operation_types=["bash", "execute", "delete", "create", "write"],
        )

        assert result is not None
        assert result.strategy == RoutingStrategy.ORCHESTRATED
        assert result.complexity.level == ComplexityLevelEnum.COMPLEX


# =============================================================================
# Full Pipeline Integration Tests
# =============================================================================


class TestFullPipelineIntegration:
    """Integration tests for the full orchestrator pipeline."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_simple_task(
        self,
        orchestrator: MainOrchestrator,
        mock_model_adapter: MagicMock,
    ) -> None:
        """Test the full pipeline for a simple task.

        This tests the complete flow:
        1. Intent recognition
        2. Complexity assessment
        3. Task routing
        4. Agent execution
        5. Result return
        """
        mock_response = ModelResponse(
            content="<final>\nThe file contains a simple hello world function.\n</final>",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            stop_reason="end_turn",
        )
        mock_model_adapter.chat.return_value = mock_response

        result = await orchestrator.execute("read the main.py file")

        assert result is not None
        assert result.success is True
        assert result.content != ""
        assert result.session_id.startswith("sess_")
        assert result.intent is not None
        assert result.intent.task_type == IntentType.CODE_READ
        assert result.complexity is not None
        assert result.routing is not None
        assert result.routing.strategy == RoutingStrategy.FASTPATH

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_with_existing_session(
        self,
        orchestrator: MainOrchestrator,
        mock_model_adapter: MagicMock,
    ) -> None:
        """Test the full pipeline with an existing session."""
        mock_response = ModelResponse(
            content="<final>\nTask completed.\n</final>",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            stop_reason="end_turn",
        )
        mock_model_adapter.chat.return_value = mock_response

        # Execute first task to create session
        first_result = await orchestrator.execute("read the main.py file")
        session_id = first_result.session_id

        # Execute second task with existing session
        second_result = await orchestrator.execute(
            "continue editing",
            session_id=session_id,
        )

        assert second_result is not None
        assert second_result.success is True
        assert second_result.session_id == session_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_tracks_all_stages(
        self,
        orchestrator: MainOrchestrator,
        mock_model_adapter: MagicMock,
    ) -> None:
        """Test that all pipeline stages are tracked in the result."""
        mock_response = ModelResponse(
            content="<final>\nAnalysis complete.\n</final>",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            stop_reason="end_turn",
        )
        mock_model_adapter.chat.return_value = mock_response

        result = await orchestrator.execute("analyze the codebase")

        # Verify all stages are tracked
        assert result.intent is not None
        assert result.intent.task_type == IntentType.ANALYSIS
        assert result.intent.scope == IntentScope.PROJECT

        assert result.complexity is not None
        assert result.complexity.score > 0

        assert result.routing is not None
        assert result.routing.strategy in [
            RoutingStrategy.FASTPATH,
            RoutingStrategy.ENHANCED,
            RoutingStrategy.ORCHESTRATED,
        ]
        assert result.agent_result is not None
        assert result.execution_time_ms >= 0


# =============================================================================
# Session Management Integration Tests
# =============================================================================


class TestSessionManagementIntegration:
    """Integration tests for session create/get/update cycle."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_create_and_get(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test creating and retrieving a session."""
        # Create session
        created = await session_manager.create_session(
            complexity_score=35,
            complexity_level=SessionComplexityLevel.SIMPLE,
            metadata={"task": "test task"},
        )

        assert created is not None
        assert created.session_id.startswith("sess_")
        assert created.complexity_score == 35

        # Get session
        retrieved = await session_manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.complexity_score == 35

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_update(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test updating a session."""
        # Create session
        created = await session_manager.create_session(
            complexity_score=50,
            complexity_level=SessionComplexityLevel.MEDIUM,
        )

        # Update session state
        created.state = SessionState.COMPLETED
        updated = await session_manager.update_session(created)

        assert updated is not None
        assert updated.state == SessionState.COMPLETED
        assert updated.updated_at >= updated.created_at

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_pause_and_resume(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test pausing and resuming a session."""
        # Create session
        created = await session_manager.create_session(
            complexity_score=35,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )

        # Pause
        paused = await session_manager.pause_session(created.session_id)
        assert paused.state == SessionState.PAUSED

        # Resume
        resumed = await session_manager.resume_session(created.session_id)
        assert resumed.state == SessionState.ACTIVE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_delete(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test deleting a session."""
        # Create session
        created = await session_manager.create_session(
            complexity_score=35,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )
        session_id = created.session_id

        # Delete
        await session_manager.delete_session(session_id)

        # Verify deletion
        from mozi.core.error import MoziSessionError
        with pytest.raises(MoziSessionError):
            await session_manager.get_session(session_id)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_list(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test listing sessions."""
        # Create multiple sessions
        await session_manager.create_session(
            complexity_score=30,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )
        await session_manager.create_session(
            complexity_score=60,
            complexity_level=SessionComplexityLevel.MEDIUM,
        )

        # List all
        sessions = await session_manager.list_sessions()
        assert len(sessions) == 2

        # Filter by state
        active_sessions = await session_manager.list_sessions(state=SessionState.ACTIVE)
        assert len(active_sessions) == 2

        # Filter by complexity
        simple_sessions = await session_manager.list_sessions(
            complexity_level=SessionComplexityLevel.SIMPLE
        )
        assert len(simple_sessions) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_exists(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test checking session existence."""
        # Create session
        created = await session_manager.create_session(
            complexity_score=35,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )

        # Check existence
        assert await session_manager.session_exists(created.session_id) is True
        assert await session_manager.session_exists("nonexistent") is False


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_task_success(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test successful task execution via CLI command."""
        mock_response = ModelResponse(
            content="<final>\nTask completed successfully.\n</final>",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            stop_reason="end_turn",
        )
        mock_model_adapter.chat.return_value = mock_response

        # Reset factory and set up with mocks
        OrchestratorFactory.reset()
        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=MainOrchestrator(
                model_adapter=mock_model_adapter,
                tool_registry=mock_tool_registry,
            ),
        ):
            result = await execute_task("read the main.py file")

            assert result is not None
            assert result.success is True
            assert result.content != ""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_task_with_session(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test task execution with a specific session via CLI."""
        mock_response = ModelResponse(
            content="<final>\nDone.\n</final>",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            stop_reason="end_turn",
        )
        mock_model_adapter.chat.return_value = mock_response

        OrchestratorFactory.reset()
        orchestrator = MainOrchestrator(
            model_adapter=mock_model_adapter,
            tool_registry=mock_tool_registry,
        )

        # Pre-create a session
        session = await orchestrator.get_session_manager().create_session(
            complexity_score=35,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=orchestrator,
        ):
            result = await execute_task(
                "continue working",
                session_id=session.session_id,
            )

            assert result is not None
            assert result.session_id == session.session_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_task_with_retry_success(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test execute_task_with_retry succeeds."""
        mock_response = ModelResponse(
            content="<final>\nCompleted.\n</final>",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            stop_reason="end_turn",
        )
        mock_model_adapter.chat.return_value = mock_response

        OrchestratorFactory.reset()
        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=MainOrchestrator(
                model_adapter=mock_model_adapter,
                tool_registry=mock_tool_registry,
            ),
        ):
            result = await execute_task_with_retry(
                "read the file",
                max_retries=3,
            )

            assert result is not None
            assert result.success is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_session(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test getting a session via CLI."""
        OrchestratorFactory.reset()
        orchestrator = MainOrchestrator(
            model_adapter=mock_model_adapter,
            tool_registry=mock_tool_registry,
        )

        # Create a session
        created = await orchestrator.get_session_manager().create_session(
            complexity_score=50,
            complexity_level=SessionComplexityLevel.MEDIUM,
        )

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=orchestrator,
        ):
            result = await get_session(created.session_id)

            assert result is not None
            assert result["session_id"] == created.session_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_session_via_cli(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test deleting a session via CLI."""
        OrchestratorFactory.reset()
        orchestrator = MainOrchestrator(
            model_adapter=mock_model_adapter,
            tool_registry=mock_tool_registry,
        )

        # Create a session
        created = await orchestrator.get_session_manager().create_session(
            complexity_score=35,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=orchestrator,
        ):
            success = await delete_session(created.session_id)
            assert success is None or success is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_sessions(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test listing sessions via session manager."""
        OrchestratorFactory.reset()
        orchestrator = MainOrchestrator(
            model_adapter=mock_model_adapter,
            tool_registry=mock_tool_registry,
        )

        # Create some sessions
        await orchestrator.get_session_manager().create_session(
            complexity_score=30,
            complexity_level=SessionComplexityLevel.SIMPLE,
        )
        await orchestrator.get_session_manager().create_session(
            complexity_score=60,
            complexity_level=SessionComplexityLevel.MEDIUM,
        )

        # Test listing via session manager directly
        sessions = await orchestrator.get_session_manager().list_sessions()
        assert len(sessions) == 2

        # Verify filtering works
        simple_sessions = await orchestrator.get_session_manager().list_sessions(
            complexity_level=SessionComplexityLevel.SIMPLE
        )
        assert len(simple_sessions) == 1
        assert simple_sessions[0].complexity_level == SessionComplexityLevel.SIMPLE


# =============================================================================
# Error Handling Integration Tests
# =============================================================================


class TestErrorHandlingIntegration:
    """Integration tests for error handling in the pipeline."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_orchestrator_handles_model_error(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
        session_manager: SessionManager,
        orchestrator_config: OrchestratorConfig,
    ) -> None:
        """Test that orchestrator handles model API errors gracefully."""
        from mozi.orchestrator.agent.base import AgentError
        from mozi.orchestrator.orchestrator import OrchestratorError

        # Make the model adapter raise an error
        mock_model_adapter.chat = AsyncMock(
            side_effect=AgentError("Model API error")
        )

        orchestrator = MainOrchestrator(
            model_adapter=mock_model_adapter,
            tool_registry=mock_tool_registry,
            session_manager=session_manager,
            config=orchestrator_config,
        )

        # The error gets wrapped in OrchestratorError
        with pytest.raises(OrchestratorError):
            await orchestrator.execute("read the file")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_not_found_error(
        self,
        orchestrator: MainOrchestrator,
    ) -> None:
        """Test that orchestrator handles missing session gracefully."""
        from mozi.orchestrator.orchestrator import OrchestratorError

        with pytest.raises(OrchestratorError):
            await orchestrator.execute(
                "continue task",
                session_id="nonexistent_session_id",
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_task_error(self) -> None:
        """Test that empty task is handled."""
        from mozi.orchestrator.core.router import RoutingError

        router = TaskRouter()

        with pytest.raises(RoutingError):
            router.route("")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cli_error_handling(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
    ) -> None:
        """Test that CLI properly wraps orchestrator errors."""
        from mozi.orchestrator.orchestrator import OrchestratorError

        mock_model_adapter.chat = AsyncMock(
            side_effect=OrchestratorError("Test error")
        )

        OrchestratorFactory.reset()
        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=MainOrchestrator(
                model_adapter=mock_model_adapter,
                tool_registry=mock_tool_registry,
            ),
        ):
            with pytest.raises(CLIError):
                await execute_task("do something")
