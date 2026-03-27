"""Complexity assessment for Mozi AI Coding Agent.

This module provides score-based complexity assessment using heuristics
to evaluate task complexity for routing decisions.

Complexity Levels
----------------
- SIMPLE: Score <= 40, single-agent FastPath
- MEDIUM: Score 41-70, enhanced monitoring
- COMPLEX: Score > 70, multi-agent orchestration

Examples
--------
Assess a simple task:

    result = assess_complexity("Read a single file")
    print(result.score)  # Low score for simple operation

Assess a complex task:

    result = assess_complexity(
        task_description="Refactor entire codebase",
        file_count=50,
        operation_types=["read", "write", "edit", "delete"],
    )
    print(result.level)  # ComplexityLevel.COMPLEX
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mozi.core.error import MoziError


class ComplexityLevel(Enum):
    """Complexity level for tasks.

    Attributes
    ----------
    SIMPLE : str
        Tasks with complexity score <= 40.
        Single-agent FastPath with implicit ReAct planning.
    MEDIUM : str
        Tasks with complexity score 41-70.
        Single-agent with enhanced monitoring.
    COMPLEX : str
        Tasks with complexity score > 70.
        Multi-agent with Orchestrator DAG scheduling.
    """

    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


class ComplexityError(MoziError):
    """Exception raised for complexity assessment errors.

    This exception is raised when complexity assessment fails due to
    invalid input or internal assessment errors.

    Attributes
    ----------
    task_description : str | None
        The task description that caused the error, if available.

    Examples
    --------
    Raise when assessment fails:

        raise ComplexityError("Failed to assess task complexity")

    Raise with task description:

        raise ComplexityError(
            "Invalid task parameters",
            task_description="Invalid task"
        )
    """

    def __init__(
        self,
        message: str,
        task_description: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize ComplexityError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        task_description : str | None, optional
            The task description that caused the error.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.task_description: str | None = task_description

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        cause_repr = repr(self.cause) if self.cause else None
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"task_description={self.task_description!r}, "
            f"cause={cause_repr})"
        )


@dataclass(frozen=True)
class TaskComplexity:
    """Immutable result of complexity assessment.

    Attributes
    ----------
    score : int
        Numerical complexity score (0-100).
    level : ComplexityLevel
        Complexity level classification.
    factors : dict[str, int]
        Breakdown of contributing factors to the score.

    Examples
    --------
    Access assessment results:

        result = assess_complexity("Refactor module")
        print(f"Score: {result.score}, Level: {result.level.value}")
        print(f"Factors: {result.factors}")
    """

    score: int
    level: ComplexityLevel
    factors: dict[str, int]

    def __post_init__(self) -> None:
        """Validate complexity score after initialization."""
        if not 0 <= self.score <= 100:
            raise ComplexityError(
                f"Complexity score must be 0-100, got {self.score}"
            )


# Heuristic weights for complexity factors
_OPERATION_WEIGHTS: dict[str, int] = {
    "read": 5,
    "glob": 5,
    "grep": 8,
    "edit": 15,
    "write": 20,
    "delete": 25,
    "bash": 30,
    "execute": 35,
    "create": 25,
}

_FILE_COUNT_THRESHOLDS: list[tuple[int | float, int]] = [
    (2, 0),       # 1 file: 0 points (1 < 2)
    (6, 5),       # 2-5 files: 5 points (2-5 < 6)
    (11, 10),     # 6-10 files: 10 points (6-10 < 11)
    (26, 20),     # 11-25 files: 20 points (11-25 < 26)
    (51, 30),     # 26-50 files: 30 points (26-50 < 51)
    (float("inf"), 40),  # 51+ files: 40 points
]

_DESCRIPTION_LENGTH_THRESHOLD = 200
_DESCRIPTION_LENGTH_PENALTY = 10


def score_to_level(score: int) -> ComplexityLevel:
    """Convert a numerical score to a complexity level.

    Parameters
    ----------
    score : int
        Complexity score (0-100).

    Returns
    -------
    ComplexityLevel
        The corresponding complexity level.

    Examples
    --------
        level = score_to_level(35)  # Returns ComplexityLevel.SIMPLE
        level = score_to_level(55)  # Returns ComplexityLevel.MEDIUM
        level = score_to_level(85)  # Returns ComplexityLevel.COMPLEX
    """
    if score <= 40:
        return ComplexityLevel.SIMPLE
    if score <= 70:
        return ComplexityLevel.MEDIUM
    return ComplexityLevel.COMPLEX


def get_complexity_level(score: int) -> ComplexityLevel:
    """Get complexity level from score (alias for score_to_level).

    This function provides a more descriptive name for converting
    scores to levels.

    Parameters
    ----------
    score : int
        Complexity score (0-100).

    Returns
    -------
    ComplexityLevel
        The corresponding complexity level.
    """
    return score_to_level(score)


class ComplexityAssessor:
    """Assessor for evaluating task complexity using heuristics.

    This class provides methods to assess task complexity based on
    various factors including operation types, file counts, and
    task descriptions.

    Examples
    --------
    Use the assessor directly:

        assessor = ComplexityAssessor()
        result = assessor.assess(
            task_description="Implement new feature",
            file_count=10,
            operation_types=["read", "write"],
        )
        print(result.score)
    """

    def __init__(
        self,
        operation_weights: dict[str, int] | None = None,
        file_thresholds: list[tuple[int | float, int]] | None = None,
    ) -> None:
        """Initialize ComplexityAssessor with optional custom weights.

        Parameters
        ----------
        operation_weights : dict[str, int] | None, optional
            Custom weights for operation types.
        file_thresholds : list[tuple[int | float, int]] | None, optional
            Custom thresholds for file count scoring.
        """
        self._operation_weights: dict[str, int] = (
            operation_weights if operation_weights is not None
            else _OPERATION_WEIGHTS.copy()
        )
        self._file_thresholds: list[tuple[int | float, int]] = (
            file_thresholds if file_thresholds is not None
            else _FILE_COUNT_THRESHOLDS
        )

    def _score_file_count(self, file_count: int) -> int:
        """Calculate complexity score contribution from file count.

        Parameters
        ----------
        file_count : int
            Number of files involved in the task.

        Returns
        -------
        int
            Score contribution from file count.
        """
        for threshold, score in self._file_thresholds:
            if file_count < threshold:
                return score
        return 0

    def _score_operations(self, operation_types: list[str]) -> int:
        """Calculate complexity score from operation types.

        Parameters
        ----------
        operation_types : list[str]
            List of operation type names.

        Returns
        -------
        int
            Score contribution from operations.
        """
        total = 0
        for op in operation_types:
            op_lower = op.lower()
            total += self._operation_weights.get(op_lower, 10)
        return total

    def _score_description(self, description: str) -> int:
        """Calculate complexity score from description length.

        Longer descriptions may indicate more complex tasks.

        Parameters
        ----------
        description : str
            Task description text.

        Returns
        -------
        int
            Score contribution from description length.
        """
        if len(description) > _DESCRIPTION_LENGTH_THRESHOLD:
            return _DESCRIPTION_LENGTH_PENALTY
        return 0

    def assess(
        self,
        task_description: str = "",
        file_count: int = 0,
        operation_types: list[str] | None = None,
    ) -> TaskComplexity:
        """Assess the complexity of a task.

        Parameters
        ----------
        task_description : str, optional
            Description of the task to assess.
        file_count : int, optional
            Number of files involved in the task.
        operation_types : list[str] | None, optional
            Types of operations involved (read, write, edit, etc.).

        Returns
        -------
        TaskComplexity
            Immutable result containing score, level, and factors.

        Raises
        ------
        ComplexityError
            If assessment fails due to invalid input.

        Examples
        --------
        Simple task:

            result = assessor.assess(
                task_description="Read one file",
                file_count=1,
                operation_types=["read"],
            )
            assert result.level == ComplexityLevel.SIMPLE

        Complex task:

            result = assessor.assess(
                task_description="Refactor multiple modules",
                file_count=30,
                operation_types=["read", "edit", "write", "delete"],
            )
            assert result.level == ComplexityLevel.COMPLEX
        """
        if file_count < 0:
            raise ComplexityError(
                "file_count must be non-negative",
                task_description=task_description,
            )

        if operation_types is None:
            operation_types = []

        # Calculate individual factor scores
        file_score = self._score_file_count(file_count)
        operation_score = self._score_operations(operation_types)
        description_score = self._score_description(task_description)

        # Sum total score, capped at 100
        total_score = min(100, file_score + operation_score + description_score)

        # Determine level from score
        level = score_to_level(total_score)

        return TaskComplexity(
            score=total_score,
            level=level,
            factors={
                "file_count": file_score,
                "operations": operation_score,
                "description": description_score,
            },
        )


# Default global assessor instance
_default_assessor: ComplexityAssessor | None = None


def get_default_assessor() -> ComplexityAssessor:
    """Get the default global ComplexityAssessor instance.

    Returns
    -------
    ComplexityAssessor
        The default assessor instance.
    """
    global _default_assessor
    if _default_assessor is None:
        _default_assessor = ComplexityAssessor()
    return _default_assessor


def assess_complexity(
    task_description: str = "",
    file_count: int = 0,
    operation_types: list[str] | None = None,
) -> TaskComplexity:
    """Assess task complexity using default heuristics.

    This is a convenience function that uses the default global
    assessor to evaluate task complexity.

    Parameters
    ----------
    task_description : str, optional
        Description of the task to assess.
    file_count : int, optional
        Number of files involved in the task.
    operation_types : list[str] | None, optional
        Types of operations involved (read, write, edit, etc.).

    Returns
    -------
    TaskComplexity
        Immutable result containing score, level, and factors.

    Examples
    --------
    Simple assessment:

        result = assess_complexity("Read a file")
        print(result.score)  # Low score

    Detailed assessment:

        result = assess_complexity(
            task_description="Implement user authentication",
            file_count=15,
            operation_types=["read", "write", "edit"],
        )
        print(f"Level: {result.level.value}")
    """
    assessor = get_default_assessor()
    return assessor.assess(
        task_description=task_description,
        file_count=file_count,
        operation_types=operation_types,
    )
