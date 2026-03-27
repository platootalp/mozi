"""Unit tests for the main orchestrator.

Tests cover:
- Orchestrator initialization
- Task execution pipeline
- Session management integration
- Routing strategy selection
- Error handling
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.orchestrator.agent.base import AgentConfig
from mozi.orchestrator.agent.runtime import AgentRuntimeResult
from mozi.orchestrator.core.complexity import (
    ComplexityAssessor,
    ComplexityLevel,
    TaskComplexity,
)
from mozi.orchestrator.core.intent import (
    IntentResult,
    IntentScope,
    IntentType,
)
from mozi.orchestrator.core.router import RouteResult, RoutingStrategy, TaskRouter
from mozi.orchestrator.orchestrator import (
    MainOrchestrator,
    OrchestratorConfig,
    OrchestratorError,
    OrchestratorResult,
)
from mozi.orchestrator.session.context import SessionContext, SessionState
from mozi.orchestrator.session.manager import SessionManager


@pytest.fixture
def mock_model_adapter() -> MagicMock:
    """Create a mock model adapter."""
    adapter = MagicMock()
    adapter.chat = AsyncMock()
    return adapter


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Create a mock tool registry."""
    registry = MagicMock()
    registry.list_tools = MagicMock(return_value=[])
    registry.execute = AsyncMock()
    return registry


@pytest.fixture
def session_manager() -> SessionManager:
    """Create a session manager instance."""
    return SessionManager()


@pytest.fixture
def complexity_assessor() -> ComplexityAssessor:
    """Create a complexity assessor instance."""
    return ComplexityAssessor()


@pytest.fixture
def task_router(complexity_assessor: ComplexityAssessor) -> TaskRouter:
    """Create a task router instance."""
    return TaskRouter(complexity_assessor=complexity_assessor)


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create an orchestrator configuration."""
    return OrchestratorConfig(
        max_fastpath_iterations=5,
        max_enhanced_iterations=15,
        max_orchestrated_iterations=30,
        enable_monitoring=True,
        default_temperature=0.7,
        default_max_tokens=1000,
    )


@pytest.fixture
def mock_agent_runtime() -> MagicMock:
    """Create a mock agent runtime."""
    runtime = MagicMock()
    runtime.run = AsyncMock()
    return runtime


@pytest.fixture
def orchestrator(
    mock_model_adapter: MagicMock,
    mock_tool_registry: MagicMock,
    session_manager: SessionManager,
    complexity_assessor: ComplexityAssessor,
    task_router: TaskRouter,
    orchestrator_config: OrchestratorConfig,
) -> MainOrchestrator:
    """Create an orchestrator instance with mocked dependencies."""
    return MainOrchestrator(
        model_adapter=mock_model_adapter,
        tool_registry=mock_tool_registry,
        session_manager=session_manager,
        complexity_assessor=complexity_assessor,
        task_router=task_router,
        config=orchestrator_config,
    )


@pytest.fixture
def mock_intent_result() -> IntentResult:
    """Create a mock intent result."""
    return IntentResult(
        task_type=IntentType.CODE_EDIT,
        scope=IntentScope.FILE,
        confidence=0.9,
        keywords=["edit", "file"],
        original_input="edit the main.py file",
    )


@pytest.fixture
def mock_task_complexity() -> TaskComplexity:
    """Create a mock task complexity."""
    return TaskComplexity(
        score=35,
        level=ComplexityLevel.SIMPLE,
        factors={"file_count": 0, "operations": 15, "description": 0},
    )


@pytest.fixture
def mock_route_result(
    mock_task_complexity: TaskComplexity, mock_intent_result: IntentResult
) -> RouteResult:
    """Create a mock route result."""
    return RouteResult(
        strategy=RoutingStrategy.FASTPATH,
        complexity=mock_task_complexity,
        intent=mock_intent_result,
        reasoning="Task assessed as SIMPLE (score=35)",
    )


@pytest.fixture
def mock_session_context() -> SessionContext:
    """Create a mock session context."""
    now = datetime.now()
    return SessionContext(
        session_id="sess_test123",
        created_at=now,
        updated_at=now,
        complexity_score=35,
        complexity_level=ComplexityLevel.SIMPLE,
        state=SessionState.ACTIVE,
        metadata={},
        messages=[],
        task_history=[],
    )


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = OrchestratorConfig()

        assert config.max_fastpath_iterations == 5
        assert config.max_enhanced_iterations == 15
        assert config.max_orchestrated_iterations == 30
        assert config.enable_monitoring is True
        assert config.default_temperature == 0.7
        assert config.default_max_tokens is None

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = OrchestratorConfig(
            max_fastpath_iterations=10,
            max_enhanced_iterations=20,
            default_temperature=0.5,
            default_max_tokens=2000,
        )

        assert config.max_fastpath_iterations == 10
        assert config.max_enhanced_iterations == 20
        assert config.default_temperature == 0.5
        assert config.default_max_tokens == 2000


class TestOrchestratorResult:
    """Tests for OrchestratorResult dataclass."""

    def test_default_result(self) -> None:
        """Test default result values."""
        result = OrchestratorResult()

        assert result.success is False
        assert result.content == ""
        assert result.session_id == ""
        assert result.intent is None
        assert result.complexity is None
        assert result.routing is None
        assert result.agent_result is None
        assert result.error is None
        assert result.execution_time_ms == 0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = OrchestratorResult(
            success=True,
            content="Task completed",
            session_id="sess_123",
            execution_time_ms=100,
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["content"] == "Task completed"
        assert d["session_id"] == "sess_123"
        assert d["execution_time_ms"] == 100


class TestOrchestratorError:
    """Tests for OrchestratorError exception."""

    def test_error_creation(self) -> None:
        """Test error creation with message."""
        error = OrchestratorError("Test error message")

        assert error.message == "Test error message"
        assert error.task_description is None
        assert error.cause is None

    def test_error_with_task_description(self) -> None:
        """Test error creation with task description."""
        error = OrchestratorError(
            "Task failed",
            task_description="edit file",
        )

        assert error.message == "Task failed"
        assert error.task_description == "edit file"

    def test_error_with_cause(self) -> None:
        """Test error creation with cause."""
        cause = ValueError("Original error")
        error = OrchestratorError("Wrapper error", cause=cause)

        assert error.message == "Wrapper error"
        assert error.cause is cause

    def test_error_repr(self) -> None:
        """Test error string representation."""
        error = OrchestratorError(
            "Test error",
            task_description="test task",
        )

        repr_str = repr(error)
        assert "OrchestratorError" in repr_str
        assert "Test error" in repr_str
        assert "test task" in repr_str


class TestMainOrchestrator:
    """Tests for MainOrchestrator class."""

    def test_orchestrator_initialization(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
        session_manager: SessionManager,
        complexity_assessor: ComplexityAssessor,
        task_router: TaskRouter,
        orchestrator_config: OrchestratorConfig,
    ) -> None:
        """Test orchestrator initializes correctly."""
        orch = MainOrchestrator(
            model_adapter=mock_model_adapter,
            tool_registry=mock_tool_registry,
            session_manager=session_manager,
            complexity_assessor=complexity_assessor,
            task_router=task_router,
            config=orchestrator_config,
        )

        assert orch._model_adapter is mock_model_adapter
        assert orch._tool_registry is mock_tool_registry
        assert orch._session_manager is session_manager
        assert orch._complexity_assessor is complexity_assessor
        assert orch._task_router is task_router
        assert orch._config is orchestrator_config

    def test_get_session_manager(self, orchestrator: MainOrchestrator) -> None:
        """Test getting session manager."""
        manager = orchestrator.get_session_manager()
        assert manager is orchestrator._session_manager

    def test_get_complexity_assessor(
        self, orchestrator: MainOrchestrator
    ) -> None:
        """Test getting complexity assessor."""
        assessor = orchestrator.get_complexity_assessor()
        assert assessor is orchestrator._complexity_assessor

    def test_get_task_router(self, orchestrator: MainOrchestrator) -> None:
        """Test getting task router."""
        router = orchestrator.get_task_router()
        assert router is orchestrator._task_router

    def test_get_max_iterations_fastpath(
        self, orchestrator: MainOrchestrator
    ) -> None:
        """Test max iterations for FASTPATH strategy."""
        iterations = orchestrator._get_max_iterations_for_strategy(
            RoutingStrategy.FASTPATH
        )
        assert iterations == orchestrator._config.max_fastpath_iterations

    def test_get_max_iterations_enhanced(
        self, orchestrator: MainOrchestrator
    ) -> None:
        """Test max iterations for ENHANCED strategy."""
        iterations = orchestrator._get_max_iterations_for_strategy(
            RoutingStrategy.ENHANCED
        )
        assert iterations == orchestrator._config.max_enhanced_iterations

    def test_get_max_iterations_orchestrated(
        self, orchestrator: MainOrchestrator
    ) -> None:
        """Test max iterations for ORCHESTRATED strategy."""
        iterations = orchestrator._get_max_iterations_for_strategy(
            RoutingStrategy.ORCHESTRATED
        )
        assert iterations == orchestrator._config.max_orchestrated_iterations


class TestOrchestratorExecute:
    """Tests for orchestrator execute method."""

    @pytest.mark.asyncio
    async def test_execute_creates_session(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that execute creates a new session when no session_id provided."""
        orchestrator._agent_runtime = mock_agent_runtime

        # Mock the router to return our mock result
        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            # Mock the agent runtime to return success
            mock_agent_result = AgentRuntimeResult(
                success=True,
                content="Done",
                iterations=2,
            )
            mock_agent_runtime.run.return_value = mock_agent_result

            result = await orchestrator.execute("edit the main.py file")

            assert result.session_id.startswith("sess_")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_uses_existing_session(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_session_context: SessionContext,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that execute uses existing session when session_id provided."""
        orchestrator._agent_runtime = mock_agent_runtime

        # Pre-create the session
        await orchestrator._session_manager.save_session(mock_session_context)

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            mock_agent_result = AgentRuntimeResult(
                success=True,
                content="Done",
                iterations=2,
            )
            mock_agent_runtime.run.return_value = mock_agent_result

            result = await orchestrator.execute(
                "continue editing",
                session_id=mock_session_context.session_id,
            )

            assert result.session_id == mock_session_context.session_id
            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_fastpath_strategy(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test execution with FASTPATH routing strategy."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Task completed",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("read the file")

            assert result.success is True
            assert result.content == "Task completed"
            assert result.routing is not None
            assert result.routing.strategy == RoutingStrategy.FASTPATH

    @pytest.mark.asyncio
    async def test_execute_enhanced_strategy(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_intent_result: IntentResult,
    ) -> None:
        """Test execution with ENHANCED routing strategy."""
        orchestrator._agent_runtime = mock_agent_runtime

        # Create route result for enhanced strategy
        enhanced_complexity = TaskComplexity(
            score=55,
            level=ComplexityLevel.MEDIUM,
            factors={"file_count": 5, "operations": 30, "description": 10},
        )
        enhanced_route = RouteResult(
            strategy=RoutingStrategy.ENHANCED,
            complexity=enhanced_complexity,
            intent=mock_intent_result,
            reasoning="Task assessed as MEDIUM",
        )

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Task completed",
            iterations=5,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=enhanced_route,
        ):
            result = await orchestrator.execute("refactor the module")

            assert result.success is True
            assert result.routing.strategy == RoutingStrategy.ENHANCED

    @pytest.mark.asyncio
    async def test_execute_orchestrated_strategy(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_intent_result: IntentResult,
    ) -> None:
        """Test execution with ORCHESTRATED routing strategy."""
        orchestrator._agent_runtime = mock_agent_runtime

        # Create route result for orchestrated strategy
        complex_intent = IntentResult(
            task_type=IntentType.ANALYSIS,
            scope=IntentScope.PROJECT,
            confidence=0.95,
            keywords=["analyze", "codebase"],
            original_input="analyze entire codebase",
        )
        complex_complexity = TaskComplexity(
            score=85,
            level=ComplexityLevel.COMPLEX,
            factors={"file_count": 30, "operations": 40, "description": 10},
        )
        orchestrated_route = RouteResult(
            strategy=RoutingStrategy.ORCHESTRATED,
            complexity=complex_complexity,
            intent=complex_intent,
            reasoning="Task assessed as COMPLEX",
        )

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Analysis complete",
            iterations=15,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=orchestrated_route,
        ):
            result = await orchestrator.execute("analyze entire codebase")

            assert result.success is True
            assert result.routing.strategy == RoutingStrategy.ORCHESTRATED

    @pytest.mark.asyncio
    async def test_execute_tracks_intent(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that execute properly tracks intent recognition."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            assert result.intent is not None
            assert result.intent.task_type == IntentType.CODE_EDIT

    @pytest.mark.asyncio
    async def test_execute_tracks_complexity(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that execute properly tracks complexity assessment."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            assert result.complexity is not None
            assert result.complexity.level == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_execute_handles_agent_failure(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that execute handles agent runtime failure."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=False,
            content="",
            iterations=5,
            error="Agent execution failed",
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            assert result.success is False
            assert result.error is not None
            assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_records_execution_time(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that execute records execution time."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            assert result.execution_time_ms >= 0


class TestOrchestratorExecuteWithRetry:
    """Tests for orchestrator execute_with_retry method."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test retry succeeds on first attempt."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute_with_retry(
                "edit the main.py file",
                max_retries=3,
            )

            assert result.success is True
            assert mock_agent_runtime.run.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_retries_on_failure(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test retry attempts on failure."""
        orchestrator._agent_runtime = mock_agent_runtime

        # First call fails, second succeeds
        mock_agent_result_fail = AgentRuntimeResult(
            success=False,
            error="Temporary failure",
        )
        mock_agent_result_success = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.side_effect = [
            mock_agent_result_fail,
            mock_agent_result_success,
        ]

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute_with_retry(
                "edit the main.py file",
                max_retries=3,
            )

            assert result.success is True
            assert mock_agent_runtime.run.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test retry fails after exhausting all attempts."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=False,
            error="Persistent failure",
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator.execute_with_retry(
                    "edit the main.py file",
                    max_retries=2,
                )

            assert "failed" in str(exc_info.value).lower()
            assert mock_agent_runtime.run.call_count == 3  # initial + 2 retries


class TestOrchestratorSessionIntegration:
    """Tests for orchestrator session management integration."""

    @pytest.mark.asyncio
    async def test_session_created_with_complexity(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that session is created with correct complexity."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            # Verify session was created with correct complexity
            session = await orchestrator._session_manager.get_session(
                result.session_id
            )
            assert session.complexity_score == mock_route_result.complexity.score
            # Compare by value since enums are from different modules
            assert session.complexity_level.value == mock_route_result.complexity.level.value

    @pytest.mark.asyncio
    async def test_session_state_updated_on_success(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that session state is updated to COMPLETED on success."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            session = await orchestrator._session_manager.get_session(
                result.session_id
            )
            assert session.state == SessionState.COMPLETED

    @pytest.mark.asyncio
    async def test_session_state_updated_on_failure(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that session state is updated to ERROR on failure."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=False,
            error="Task failed",
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute("edit the main.py file")

            session = await orchestrator._session_manager.get_session(
                result.session_id
            )
            assert session.state == SessionState.ERROR

    @pytest.mark.asyncio
    async def test_session_metadata_includes_task(
        self,
        orchestrator: MainOrchestrator,
        mock_agent_runtime: MagicMock,
        mock_route_result: RouteResult,
    ) -> None:
        """Test that session metadata includes task description."""
        orchestrator._agent_runtime = mock_agent_runtime

        mock_agent_result = AgentRuntimeResult(
            success=True,
            content="Done",
            iterations=1,
        )
        mock_agent_runtime.run.return_value = mock_agent_result

        task_description = "edit the main.py file"

        with patch.object(
            orchestrator._task_router,
            "route",
            return_value=mock_route_result,
        ):
            result = await orchestrator.execute(task_description)

            session = await orchestrator._session_manager.get_session(
                result.session_id
            )
            assert session.metadata.get("task_description") == task_description
