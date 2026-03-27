"""Task routing module for Mozi AI Coding Agent.

This module provides task routing based on complexity assessment and intent
recognition. It determines the appropriate execution strategy for tasks.

Routing Logic
-------------
- SIMPLE (score <= 40): Single-agent FastPath with implicit ReAct planning
- MEDIUM (score 41-70): Single-agent with enhanced monitoring
- COMPLEX (score > 70): Multi-agent with Orchestrator DAG scheduling

Examples
--------
Route a simple task:

    router = TaskRouter()
    result = router.route("Read the main.py file")
    print(result.strategy)  # RoutingStrategy.FASTPATH

Route a medium complexity task:

    result = router.route(
        task_description="Analyze codebase structure",
        file_count=10,
        operation_types=["read", "grep"],
    )
    print(result.strategy)  # RoutingStrategy.ENHANCED
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from mozi.core.error import MoziError
from mozi.orchestrator.core.complexity import (
    ComplexityAssessor,
    ComplexityLevel,
    TaskComplexity,
)
from mozi.orchestrator.core.intent import (
    IntentResult,
    IntentType,
    recognize_intent,
)


class RoutingStrategy(Enum):
    """Enumeration of routing strategies.

    Attributes
    ----------
    FASTPATH : str
        Direct single-agent execution for SIMPLE tasks.
        Uses implicit ReAct planning without explicit orchestration.
    ENHANCED : str
        Single-agent execution with enhanced monitoring for MEDIUM tasks.
        Includes progress tracking and error recovery.
    ORCHESTRATED : str
        Multi-agent orchestration with DAG scheduling for COMPLEX tasks.
        Requires explicit planning and agent coordination.
    """

    FASTPATH = "FASTPATH"
    ENHANCED = "ENHANCED"
    ORCHESTRATED = "ORCHESTRATED"


class RoutingError(MoziError):
    """Exception raised when task routing fails.

    This exception is raised when the routing process cannot determine
    an appropriate strategy for a task.

    Examples
    --------
    Raise when routing input is invalid:

        raise RoutingError("Task description cannot be empty")
    """

    pass


@dataclass
class RouteResult:
    """Result of task routing.

    This dataclass holds the routing decision including the selected
    strategy, complexity assessment, and intent recognition results.

    Attributes
    ----------
    strategy : RoutingStrategy
        The selected routing strategy.
    complexity : TaskComplexity
        The complexity assessment result.
    intent : IntentResult
        The intent recognition result.
    reasoning : str
        Human-readable explanation of the routing decision.

    Examples
    --------
    Access routing results:

        result = router.route("Implement new feature")
        print(f"Strategy: {result.strategy.value}")
        print(f"Complexity: {result.complexity.level.value}")
        print(f"Reasoning: {result.reasoning}")
    """

    strategy: RoutingStrategy
    complexity: TaskComplexity
    intent: IntentResult
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        """Convert route result to dictionary.

        Returns
        -------
        dict
            Dictionary representation of the route result.
        """
        return {
            "strategy": self.strategy.value,
            "complexity_score": self.complexity.score,
            "complexity_level": self.complexity.level.value,
            "intent_type": self.intent.task_type.value,
            "intent_scope": self.intent.scope.value,
            "reasoning": self.reasoning,
        }


def complexity_level_to_strategy(level: ComplexityLevel) -> RoutingStrategy:
    """Convert complexity level to routing strategy.

    Parameters
    ----------
    level : ComplexityLevel
        The complexity level to convert.

    Returns
    -------
    RoutingStrategy
        The corresponding routing strategy.

    Examples
    --------
        strategy = complexity_level_to_strategy(ComplexityLevel.SIMPLE)
        assert strategy == RoutingStrategy.FASTPATH
    """
    if level == ComplexityLevel.SIMPLE:
        return RoutingStrategy.FASTPATH
    if level == ComplexityLevel.MEDIUM:
        return RoutingStrategy.ENHANCED
    return RoutingStrategy.ORCHESTRATED


class TaskRouter:
    """Router for determining task execution strategy.

    This class combines complexity assessment and intent recognition
    to determine the appropriate routing strategy for tasks.

    Examples
    --------
    Use the router directly:

        router = TaskRouter()
        result = router.route("Edit the config file")
        print(result.strategy)  # RoutingStrategy.FASTPATH

    Use with custom assessor and recognizer:

        assessor = ComplexityAssessor()
        router = TaskRouter(complexity_assessor=assessor)
        result = router.route("Analyze repository")
    """

    def __init__(
        self,
        complexity_assessor: ComplexityAssessor | None = None,
    ) -> None:
        """Initialize TaskRouter with optional custom assessor.

        Parameters
        ----------
        complexity_assessor : ComplexityAssessor | None, optional
            Custom complexity assessor to use. If not provided,
            uses the default ComplexityAssessor instance.
        """
        self._complexity_assessor: ComplexityAssessor = (
            complexity_assessor if complexity_assessor is not None else ComplexityAssessor()
        )

    def _infer_operation_types(self, intent: IntentResult) -> list[str]:
        """Infer operation types from intent recognition result.

        Parameters
        ----------
        intent : IntentResult
            The intent recognition result.

        Returns
        -------
        list[str]
            List of inferred operation types.
        """
        operation_map: dict[IntentType, list[str]] = {
            IntentType.CODE_EDIT: ["edit", "write"],
            IntentType.CODE_READ: ["read", "grep"],
            IntentType.BASH: ["bash", "execute"],
            IntentType.ANALYSIS: ["read", "grep", "analyze"],
            IntentType.UNKNOWN: ["read"],
        }
        return operation_map.get(intent.task_type, ["read"])

    def route(
        self,
        task_description: str,
        file_count: int | None = None,
        operation_types: list[str] | None = None,
    ) -> RouteResult:
        """Route a task based on complexity and intent.

        This method assesses the task complexity and recognizes intent
        to determine the appropriate routing strategy.

        Parameters
        ----------
        task_description : str
            Natural language description of the task.
        file_count : int | None, optional
            Number of files involved in the task. If not provided,
            inferred from intent scope.
        operation_types : list[str] | None, optional
            Types of operations involved. If not provided, inferred
            from intent type.

        Returns
        -------
        RouteResult
            The routing decision with strategy, complexity, and intent.

        Raises
        ------
        RoutingError
            If routing fails due to invalid input or processing error.

        Examples
        --------
        Simple task:

            result = router.route("Read the main.py file")
            assert result.strategy == RoutingStrategy.FASTPATH

        Medium complexity task:

            result = router.route(
                task_description="Refactor multiple modules",
                file_count=15,
                operation_types=["read", "edit", "write"],
            )
            assert result.strategy == RoutingStrategy.ENHANCED
        """
        if not task_description or not isinstance(task_description, str):
            raise RoutingError("Task description must be a non-empty string")

        # Recognize intent first
        intent = recognize_intent(task_description)

        # Infer operation types if not provided
        if operation_types is None:
            operation_types = self._infer_operation_types(intent)

        # Infer file count if not provided
        if file_count is None:
            # Estimate based on intent scope
            from mozi.orchestrator.core.intent import IntentScope

            if intent.scope == IntentScope.FILE:
                file_count = 1
            elif intent.scope == IntentScope.MULTIPLE:
                file_count = 5
            elif intent.scope == IntentScope.PROJECT:
                file_count = 10
            else:
                file_count = 1

        # Assess complexity
        complexity = self._complexity_assessor.assess(
            task_description=task_description,
            file_count=file_count,
            operation_types=operation_types,
        )

        # Determine routing strategy
        strategy = complexity_level_to_strategy(complexity.level)

        # Generate reasoning
        reasoning = (
            f"Task assessed as {complexity.level.value} "
            f"(score={complexity.score}) with intent {intent.task_type.value} "
            f"({intent.scope.value} scope) -> {strategy.value}"
        )

        return RouteResult(
            strategy=strategy,
            complexity=complexity,
            intent=intent,
            reasoning=reasoning,
        )


# Default global router instance
_default_router: TaskRouter | None = None


def get_default_router() -> TaskRouter:
    """Get the default global TaskRouter instance.

    Returns
    -------
    TaskRouter
        The default router instance.
    """
    global _default_router
    if _default_router is None:
        _default_router = TaskRouter()
    return _default_router


def route_task(
    task_description: str,
    file_count: int | None = None,
    operation_types: list[str] | None = None,
) -> RouteResult:
    """Route a task using the default router.

    This is a convenience function that uses the default global
    router to determine the appropriate routing strategy.

    Parameters
    ----------
    task_description : str
        Natural language description of the task.
    file_count : int | None, optional
        Number of files involved in the task.
    operation_types : list[str] | None, optional
        Types of operations involved.

    Returns
    -------
    RouteResult
        The routing decision with strategy, complexity, and intent.

    Examples
    --------
    Route a simple task:

        result = route_task("Read the config file")
        print(result.strategy)  # RoutingStrategy.FASTPATH
    """
    router = get_default_router()
    return router.route(
        task_description=task_description,
        file_count=file_count,
        operation_types=operation_types,
    )
