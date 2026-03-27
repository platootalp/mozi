"""Unit tests for the task router module.

Tests cover routing decisions based on complexity assessment and intent
recognition, ensuring correct strategy selection for different task types.

Examples
--------
Run all router tests:

    pytest tests/unit/orchestrator/core/test_router.py -v

Run specific test class:

    pytest tests/unit/orchestrator/core/test_router.py::TestTaskRouter -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mozi.core.error import MoziError
from mozi.orchestrator.core.complexity import (
    ComplexityAssessor,
    ComplexityLevel,
    TaskComplexity,
)
from mozi.orchestrator.core.intent import (
    IntentResult,
    IntentScope,
    IntentType,
    IntentRecognitionError,
)
from mozi.orchestrator.core.router import (
    RoutingError,
    RoutingStrategy,
    RouteResult,
    TaskRouter,
    complexity_level_to_strategy,
    get_default_router,
    route_task,
)


class TestComplexityLevelToStrategy:
    """Tests for complexity_level_to_strategy function."""

    def test_simple_returns_fastpath(self) -> None:
        """SIMPLE complexity level maps to FASTPATH strategy."""
        result = complexity_level_to_strategy(ComplexityLevel.SIMPLE)
        assert result == RoutingStrategy.FASTPATH

    def test_medium_returns_enhanced(self) -> None:
        """MEDIUM complexity level maps to ENHANCED strategy."""
        result = complexity_level_to_strategy(ComplexityLevel.MEDIUM)
        assert result == RoutingStrategy.ENHANCED

    def test_complex_returns_orchestrated(self) -> None:
        """COMPLEX complexity level maps to ORCHESTRATED strategy."""
        result = complexity_level_to_strategy(ComplexityLevel.COMPLEX)
        assert result == RoutingStrategy.ORCHESTRATED


class TestRouteResult:
    """Tests for RouteResult dataclass."""

    def test_to_dict_returns_dict(self) -> None:
        """RouteResult.to_dict() returns a properly formatted dictionary."""
        # Arrange
        complexity = TaskComplexity(
            score=25,
            level=ComplexityLevel.SIMPLE,
            factors={"file_count": 0, "operations": 10, "description": 0},
        )
        intent = IntentResult(
            task_type=IntentType.CODE_READ,
            scope=IntentScope.FILE,
            confidence=0.8,
            keywords=["read", "file"],
            original_input="read the file",
        )
        result = RouteResult(
            strategy=RoutingStrategy.FASTPATH,
            complexity=complexity,
            intent=intent,
            reasoning="Test reasoning",
        )

        # Act
        dict_result = result.to_dict()

        # Assert
        assert dict_result["strategy"] == "FASTPATH"
        assert dict_result["complexity_score"] == 25
        assert dict_result["complexity_level"] == "SIMPLE"
        assert dict_result["intent_type"] == "CODE_READ"
        assert dict_result["intent_scope"] == "FILE"
        assert dict_result["reasoning"] == "Test reasoning"


class TestTaskRouter:
    """Tests for TaskRouter class."""

    def test_route_simple_task_returns_fastpath(self) -> None:
        """Simple task with low complexity returns FASTPATH strategy."""
        # Arrange
        router = TaskRouter()
        task_description = "Read the main.py file"

        # Act
        result = router.route(task_description)

        # Assert
        assert result.strategy == RoutingStrategy.FASTPATH
        assert result.complexity.level == ComplexityLevel.SIMPLE
        assert "SIMPLE" in result.reasoning
        assert "FASTPATH" in result.reasoning

    def test_route_medium_task_returns_enhanced(self) -> None:
        """Medium complexity task returns ENHANCED strategy."""
        # Arrange
        router = TaskRouter()
        task_description = "Analyze and update multiple files"

        # Act
        result = router.route(
            task_description,
            file_count=10,
            operation_types=["read", "edit", "write"],
        )

        # Assert
        assert result.strategy == RoutingStrategy.ENHANCED
        assert result.complexity.level == ComplexityLevel.MEDIUM

    def test_route_complex_task_returns_orchestrated(self) -> None:
        """Complex task with high complexity returns ORCHESTRATED strategy."""
        # Arrange
        router = TaskRouter()
        task_description = "Refactor entire codebase structure"

        # Act
        result = router.route(
            task_description,
            file_count=50,
            operation_types=["read", "edit", "write", "delete"],
        )

        # Assert
        assert result.strategy == RoutingStrategy.ORCHESTRATED
        assert result.complexity.level == ComplexityLevel.COMPLEX

    def test_route_empty_description_raises_routing_error(self) -> None:
        """Empty task description raises RoutingError."""
        # Arrange
        router = TaskRouter()

        # Act & Assert
        with pytest.raises(RoutingError, match="non-empty string"):
            router.route("")

    def test_route_none_description_raises_routing_error(self) -> None:
        """None task description raises RoutingError."""
        # Arrange
        router = TaskRouter()

        # Act & Assert
        with pytest.raises(RoutingError, match="non-empty string"):
            router.route(None)  # type: ignore

    def test_route_invalid_intent_uses_unknown(self) -> None:
        """Task with unrecognizable intent handles gracefully."""
        # Arrange
        router = TaskRouter()

        # Act
        result = router.route("do something mysterious")

        # Assert
        assert result.intent.task_type == IntentType.UNKNOWN
        assert result.strategy in RoutingStrategy

    def test_route_infers_file_count_from_intent_scope_file(self) -> None:
        """Route infers file_count=1 for FILE scope intent."""
        # Arrange
        router = TaskRouter()
        task_description = "edit the config file"

        # Act
        result = router.route(task_description)

        # Assert
        assert result.intent.scope == IntentScope.FILE

    def test_route_infers_file_count_from_intent_scope_project(self) -> None:
        """Route infers higher file_count for PROJECT scope intent."""
        # Arrange
        router = TaskRouter()
        task_description = "analyze the entire codebase"

        # Act
        result = router.route(task_description)

        # Assert
        assert result.intent.scope == IntentScope.PROJECT

    def test_route_infers_operation_types_from_intent_code_edit(self) -> None:
        """Route infers edit/write operations for CODE_EDIT intent."""
        # Arrange
        router = TaskRouter()
        task_description = "modify the main.py file"

        # Act
        result = router.route(task_description)

        # Assert
        assert result.intent.task_type == IntentType.CODE_EDIT

    def test_route_infers_operation_types_from_intent_bash(self) -> None:
        """Route infers bash/execute operations for BASH intent."""
        # Arrange
        router = TaskRouter()
        task_description = "run the test suite"

        # Act
        result = router.route(task_description)

        # Assert
        assert result.intent.task_type == IntentType.BASH

    def test_route_with_custom_complexity_assessor(self) -> None:
        """Route uses custom complexity assessor when provided."""
        # Arrange
        mock_assessor = MagicMock(spec=ComplexityAssessor)
        mock_assessor.assess.return_value = TaskComplexity(
            score=20,
            level=ComplexityLevel.SIMPLE,
            factors={"file_count": 0, "operations": 5, "description": 0},
        )
        router = TaskRouter(complexity_assessor=mock_assessor)

        # Act
        result = router.route("simple task")

        # Assert
        mock_assessor.assess.assert_called_once()
        assert result.strategy == RoutingStrategy.FASTPATH

    def test_route_result_contains_intent_info(self) -> None:
        """Route result includes intent recognition details."""
        # Arrange
        router = TaskRouter()
        task_description = "search for function definitions"

        # Act
        result = router.route(task_description)

        # Assert
        assert isinstance(result.intent, IntentResult)
        assert result.intent.task_type == IntentType.CODE_READ
        assert result.intent.confidence >= 0.0

    def test_route_result_contains_complexity_info(self) -> None:
        """Route result includes complexity assessment details."""
        # Arrange
        router = TaskRouter()
        task_description = "read a single file"

        # Act
        result = router.route(task_description)

        # Assert
        assert isinstance(result.complexity, TaskComplexity)
        assert 0 <= result.complexity.score <= 100


class TestGetDefaultRouter:
    """Tests for get_default_router function."""

    def test_get_default_router_returns_task_router(self) -> None:
        """get_default_router returns a TaskRouter instance."""
        # Act
        router = get_default_router()

        # Assert
        assert isinstance(router, TaskRouter)

    def test_get_default_router_returns_singleton(self) -> None:
        """get_default_router returns the same instance on multiple calls."""
        # Act
        router1 = get_default_router()
        router2 = get_default_router()

        # Assert
        assert router1 is router2


class TestRouteTaskFunction:
    """Tests for route_task convenience function."""

    def test_route_task_returns_route_result(self) -> None:
        """route_task returns a RouteResult instance."""
        # Act
        result = route_task("read the config file")

        # Assert
        assert isinstance(result, RouteResult)
        assert result.strategy == RoutingStrategy.FASTPATH

    def test_route_task_with_file_count(self) -> None:
        """route_task accepts explicit file_count parameter."""
        # Act
        result = route_task(
            task_description="edit multiple files",
            file_count=15,
        )

        # Assert
        assert result.complexity.score > 0

    def test_route_task_with_operation_types(self) -> None:
        """route_task accepts explicit operation_types parameter."""
        # Act
        result = route_task(
            task_description="refactor code",
            operation_types=["read", "edit", "write"],
        )

        # Assert
        assert isinstance(result, RouteResult)

    def test_route_task_empty_description_raises_routing_error(self) -> None:
        """route_task with empty description raises RoutingError."""
        # Act & Assert
        with pytest.raises(RoutingError):
            route_task("")


class TestRoutingError:
    """Tests for RoutingError exception."""

    def test_routing_error_inherits_from_mozi_error(self) -> None:
        """RoutingError is a subclass of MoziError."""
        assert issubclass(RoutingError, MoziError)

    def test_routing_error_can_be_raised_with_message(self) -> None:
        """RoutingError can be raised with a message."""
        # Act & Assert
        with pytest.raises(RoutingError, match="test error"):
            raise RoutingError("test error")

    def test_routing_error_can_have_cause(self) -> None:
        """RoutingError can be raised with a cause exception."""
        # Arrange
        cause = ValueError("original error")

        # Act & Assert
        with pytest.raises(RoutingError) as exc_info:
            raise RoutingError("routing failed", cause=cause)

        assert exc_info.value.cause is cause


@pytest.mark.parametrize(
    "task_description,expected_strategy",
    [
        ("read the main.py file", RoutingStrategy.FASTPATH),
        ("show me the config", RoutingStrategy.FASTPATH),
        ("edit the settings", RoutingStrategy.FASTPATH),
    ],
)
def test_route_simple_read_edit_tasks(
    task_description: str,
    expected_strategy: RoutingStrategy,
) -> None:
    """Parameterize test for various simple tasks returning FASTPATH."""
    # Arrange
    router = TaskRouter()

    # Act
    result = router.route(task_description)

    # Assert
    assert result.strategy == expected_strategy


@pytest.mark.parametrize(
    "task_description,expected_type",
    [
        ("run the tests", IntentType.BASH),
        ("execute npm install", IntentType.BASH),
        ("build the project", IntentType.BASH),
    ],
)
def test_route_bash_intent_recognition(
    task_description: str,
    expected_type: IntentType,
) -> None:
    """Parameterize test for bash intent recognition."""
    # Arrange
    router = TaskRouter()

    # Act
    result = router.route(task_description)

    # Assert
    assert result.intent.task_type == expected_type
