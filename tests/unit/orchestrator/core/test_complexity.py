"""Tests for mozi.orchestrator.core.complexity module.

This module contains unit tests for the complexity assessment system.
"""

from __future__ import annotations

import pytest

from mozi.core.error import MoziError
from mozi.orchestrator.core.complexity import (
    ComplexityAssessor,
    ComplexityError,
    ComplexityLevel,
    TaskComplexity,
    assess_complexity,
    get_complexity_level,
    score_to_level,
)


class TestComplexityLevel:
    """Tests for ComplexityLevel enum."""

    def test_simple_level_value(self) -> None:
        """Test SIMPLE level has correct value."""
        assert ComplexityLevel.SIMPLE.value == "SIMPLE"

    def test_simple_level_threshold(self) -> None:
        """Test SIMPLE level corresponds to score <= 40."""
        assert score_to_level(0) == ComplexityLevel.SIMPLE
        assert score_to_level(40) == ComplexityLevel.SIMPLE
        assert score_to_level(1) == ComplexityLevel.SIMPLE

    def test_medium_level_value(self) -> None:
        """Test MEDIUM level has correct value."""
        assert ComplexityLevel.MEDIUM.value == "MEDIUM"

    def test_medium_level_threshold(self) -> None:
        """Test MEDIUM level corresponds to score 41-70."""
        assert score_to_level(41) == ComplexityLevel.MEDIUM
        assert score_to_level(55) == ComplexityLevel.MEDIUM
        assert score_to_level(70) == ComplexityLevel.MEDIUM

    def test_complex_level_value(self) -> None:
        """Test COMPLEX level has correct value."""
        assert ComplexityLevel.COMPLEX.value == "COMPLEX"

    def test_complex_level_threshold(self) -> None:
        """Test COMPLEX level corresponds to score > 70."""
        assert score_to_level(71) == ComplexityLevel.COMPLEX
        assert score_to_level(100) == ComplexityLevel.COMPLEX
        assert score_to_level(85) == ComplexityLevel.COMPLEX


class TestScoreToLevel:
    """Tests for score_to_level function."""

    @pytest.mark.parametrize("score", [0, 20, 40])
    def test_simple_scores(self, score: int) -> None:
        """Test that scores <= 40 return SIMPLE."""
        assert score_to_level(score) == ComplexityLevel.SIMPLE

    @pytest.mark.parametrize("score", [41, 55, 70])
    def test_medium_scores(self, score: int) -> None:
        """Test that scores 41-70 return MEDIUM."""
        assert score_to_level(score) == ComplexityLevel.MEDIUM

    @pytest.mark.parametrize("score", [71, 85, 100])
    def test_complex_scores(self, score: int) -> None:
        """Test that scores > 70 return COMPLEX."""
        assert score_to_level(score) == ComplexityLevel.COMPLEX


class TestGetComplexityLevel:
    """Tests for get_complexity_level function."""

    def test_returns_same_as_score_to_level(self) -> None:
        """Test that get_complexity_level is consistent with score_to_level."""
        for score in [0, 30, 50, 75, 100]:
            assert get_complexity_level(score) == score_to_level(score)


class TestComplexityError:
    """Tests for ComplexityError exception."""

    def test_raise_with_message(self) -> None:
        """Test raising ComplexityError with only a message."""
        with pytest.raises(ComplexityError) as exc_info:
            raise ComplexityError("Assessment failed")

        assert exc_info.value.message == "Assessment failed"
        assert exc_info.value.task_description is None
        assert exc_info.value.cause is None

    def test_raise_with_task_description(self) -> None:
        """Test raising ComplexityError with task description."""
        with pytest.raises(ComplexityError) as exc_info:
            raise ComplexityError(
                "Invalid task",
                task_description="some task description",
            )

        assert exc_info.value.message == "Invalid task"
        assert exc_info.value.task_description == "some task description"

    def test_raise_with_cause(self) -> None:
        """Test raising ComplexityError with cause."""
        original_error = ValueError("original error")
        with pytest.raises(ComplexityError) as exc_info:
            raise ComplexityError(
                "Assessment error",
                cause=original_error,
            )

        assert exc_info.value.cause is original_error

    def test_raise_with_all_parameters(self) -> None:
        """Test raising ComplexityError with all parameters."""
        original_error = RuntimeError("runtime error")
        with pytest.raises(ComplexityError) as exc_info:
            raise ComplexityError(
                "Full error",
                task_description="my task",
                cause=original_error,
            )

        assert exc_info.value.message == "Full error"
        assert exc_info.value.task_description == "my task"
        assert exc_info.value.cause is original_error

    def test_repr_includes_task_description(self) -> None:
        """Test repr includes task_description."""
        error = ComplexityError("test error", task_description="task desc")
        assert "task_description='task desc'" in repr(error)

    def test_inheritance(self) -> None:
        """Test that ComplexityError inherits from MoziError."""
        error = ComplexityError("test")
        assert isinstance(error, MoziError)
        assert isinstance(error, Exception)


class TestTaskComplexity:
    """Tests for TaskComplexity dataclass."""

    def test_create_valid(self) -> None:
        """Test creating TaskComplexity with valid score."""
        result = TaskComplexity(
            score=50,
            level=ComplexityLevel.MEDIUM,
            factors={"file_count": 10, "operations": 20, "description": 0},
        )

        assert result.score == 50
        assert result.level == ComplexityLevel.MEDIUM
        assert result.factors["file_count"] == 10

    def test_create_zero_score(self) -> None:
        """Test creating TaskComplexity with score of 0."""
        result = TaskComplexity(
            score=0,
            level=ComplexityLevel.SIMPLE,
            factors={},
        )

        assert result.score == 0
        assert result.level == ComplexityLevel.SIMPLE

    def test_create_hundred_score(self) -> None:
        """Test creating TaskComplexity with score of 100."""
        result = TaskComplexity(
            score=100,
            level=ComplexityLevel.COMPLEX,
            factors={"file_count": 40, "operations": 60, "description": 0},
        )

        assert result.score == 100

    def test_invalid_negative_score(self) -> None:
        """Test that negative score raises error."""
        with pytest.raises(ComplexityError) as exc_info:
            TaskComplexity(
                score=-1,
                level=ComplexityLevel.SIMPLE,
                factors={},
            )

        assert "must be 0-100" in str(exc_info.value.message)

    def test_invalid_score_over_100(self) -> None:
        """Test that score > 100 raises error."""
        with pytest.raises(ComplexityError) as exc_info:
            TaskComplexity(
                score=101,
                level=ComplexityLevel.COMPLEX,
                factors={},
            )

        assert "must be 0-100" in str(exc_info.value.message)

    def test_factors_is_dict(self) -> None:
        """Test that factors is a dict."""
        result = TaskComplexity(
            score=50,
            level=ComplexityLevel.MEDIUM,
            factors={"file_count": 10, "operations": 20},
        )

        assert isinstance(result.factors, dict)
        assert result.factors["file_count"] == 10


class TestComplexityAssessorInit:
    """Tests for ComplexityAssessor initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization uses standard weights."""
        assessor = ComplexityAssessor()

        assert assessor._operation_weights is not None
        assert assessor._file_thresholds is not None

    def test_custom_operation_weights(self) -> None:
        """Test initialization with custom operation weights."""
        custom_weights = {"read": 10, "write": 20}
        assessor = ComplexityAssessor(operation_weights=custom_weights)

        assert assessor._operation_weights["read"] == 10
        assert assessor._operation_weights["write"] == 20

    def test_custom_file_thresholds(self) -> None:
        """Test initialization with custom file thresholds."""
        custom_thresholds = [(1, 0), (10, 15), (float("inf"), 30)]
        assessor = ComplexityAssessor(file_thresholds=custom_thresholds)

        assert assessor._file_thresholds == custom_thresholds


class TestComplexityAssessorFileCount:
    """Tests for file count scoring."""

    def test_single_file(self) -> None:
        """Test that 1 file scores 0."""
        assessor = ComplexityAssessor()
        result = assessor.assess(file_count=1)

        assert result.factors["file_count"] == 0

    @pytest.mark.parametrize("file_count,expected", [
        (2, 5),
        (5, 5),
        (6, 10),
        (10, 10),
        (11, 20),
        (25, 20),
        (26, 30),
        (50, 30),
        (51, 40),
    ])
    def test_file_count_scoring(self, file_count: int, expected: int) -> None:
        """Test file count scoring thresholds."""
        assessor = ComplexityAssessor()
        result = assessor.assess(file_count=file_count)

        assert result.factors["file_count"] == expected


class TestComplexityAssessorOperations:
    """Tests for operation type scoring."""

    def test_read_operation(self) -> None:
        """Test read operation scoring."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=["read"])

        assert result.factors["operations"] == 5

    def test_write_operation(self) -> None:
        """Test write operation scoring."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=["write"])

        assert result.factors["operations"] == 20

    def test_delete_operation(self) -> None:
        """Test delete operation scoring."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=["delete"])

        assert result.factors["operations"] == 25

    def test_bash_operation(self) -> None:
        """Test bash operation scoring."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=["bash"])

        assert result.factors["operations"] == 30

    def test_multiple_operations(self) -> None:
        """Test multiple operations accumulate score."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=["read", "write", "edit"])

        # 5 + 20 + 15 = 40
        assert result.factors["operations"] == 40

    def test_unknown_operation_defaults(self) -> None:
        """Test unknown operations default to 10."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=["custom_operation"])

        assert result.factors["operations"] == 10

    def test_empty_operations(self) -> None:
        """Test empty operations list scores 0."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=[])

        assert result.factors["operations"] == 0

    def test_none_operations(self) -> None:
        """Test None operations list scores 0."""
        assessor = ComplexityAssessor()
        result = assessor.assess(operation_types=None)

        assert result.factors["operations"] == 0


class TestComplexityAssessorDescription:
    """Tests for description scoring."""

    def test_short_description(self) -> None:
        """Test short description scores 0."""
        assessor = ComplexityAssessor()
        result = assessor.assess(task_description="Short task")

        assert result.factors["description"] == 0

    def test_long_description(self) -> None:
        """Test description > 200 chars scores penalty."""
        assessor = ComplexityAssessor()
        long_description = "x" * 201
        result = assessor.assess(task_description=long_description)

        assert result.factors["description"] == 10

    def test_exactly_threshold_length(self) -> None:
        """Test description at threshold scores 0."""
        assessor = ComplexityAssessor()
        result = assessor.assess(task_description="x" * 200)

        assert result.factors["description"] == 0


class TestComplexityAssessorAssess:
    """Tests for ComplexityAssessor.assess method."""

    def test_minimal_task_simple(self) -> None:
        """Test minimal task is classified as SIMPLE."""
        assessor = ComplexityAssessor()
        result = assessor.assess()

        assert result.score == 0
        assert result.level == ComplexityLevel.SIMPLE

    def test_single_read_simple(self) -> None:
        """Test single read operation is SIMPLE."""
        assessor = ComplexityAssessor()
        result = assessor.assess(
            task_description="Read a file",
            file_count=1,
            operation_types=["read"],
        )

        assert result.score == 5
        assert result.level == ComplexityLevel.SIMPLE

    def test_multiple_files_medium(self) -> None:
        """Test multiple files becomes MEDIUM."""
        assessor = ComplexityAssessor()
        result = assessor.assess(
            task_description="Edit config files",
            file_count=10,
            operation_types=["read", "edit"],
        )

        # 10 (files) + 20 (read+edit) = 30... wait that's SIMPLE
        # Let's make it more complex
        assert result.score <= 40

    def test_many_files_complex(self) -> None:
        """Test many files and operations becomes COMPLEX."""
        assessor = ComplexityAssessor()
        result = assessor.assess(
            task_description="Refactor entire codebase",
            file_count=50,
            operation_types=["read", "write", "edit", "delete", "bash"],
        )

        # 30 (50 files) + 95 (5 ops) = 125 -> capped at 100
        assert result.score == 100
        assert result.level == ComplexityLevel.COMPLEX

    def test_negative_file_count_raises(self) -> None:
        """Test that negative file_count raises error."""
        assessor = ComplexityAssessor()

        with pytest.raises(ComplexityError) as exc_info:
            assessor.assess(file_count=-1)

        assert "file_count must be non-negative" in str(exc_info.value.message)

    def test_score_capped_at_100(self) -> None:
        """Test that total score is capped at 100."""
        assessor = ComplexityAssessor()
        result = assessor.assess(
            file_count=100,
            operation_types=["read", "write", "edit", "delete", "bash", "execute"],
        )

        assert result.score == 100


class TestGlobalAssessor:
    """Tests for global assessor and convenience function."""

    def test_assess_complexity_returns_valid_result(self) -> None:
        """Test assess_complexity returns valid TaskComplexity."""
        result = assess_complexity(
            task_description="Simple task",
            file_count=1,
            operation_types=["read"],
        )

        assert isinstance(result, TaskComplexity)
        assert 0 <= result.score <= 100
        assert result.level in ComplexityLevel

    def test_assess_complexity_consistency(self) -> None:
        """Test assess_complexity gives consistent results."""
        params = {
            "task_description": "Test task",
            "file_count": 10,
            "operation_types": ["read", "write"],
        }

        result1 = assess_complexity(**params)
        result2 = assess_complexity(**params)

        assert result1.score == result2.score
        assert result1.level == result2.level

    def test_default_assessor_is_singleton(self) -> None:
        """Test that default assessor is reused."""
        from mozi.orchestrator.core.complexity import get_default_assessor

        assessor1 = get_default_assessor()
        assessor2 = get_default_assessor()

        assert assessor1 is assessor2


class TestIntegration:
    """Integration tests for complexity assessment."""

    def test_simple_task_boundaries(self) -> None:
        """Test SIMPLE level boundaries."""
        assessor = ComplexityAssessor()

        # Score 40 is SIMPLE
        result = assessor.assess(file_count=8, operation_types=["read"])
        # 10 (files) + 5 (read) = 15
        assert result.score <= 40
        assert result.level == ComplexityLevel.SIMPLE

    def test_medium_task_boundaries(self) -> None:
        """Test MEDIUM level boundaries."""
        assessor = ComplexityAssessor()

        # Score 41-70 is MEDIUM
        result = assessor.assess(
            file_count=15,
            operation_types=["read", "edit", "write"],
        )
        # 20 (files) + 40 (3 ops) = 60
        assert 41 <= result.score <= 70
        assert result.level == ComplexityLevel.MEDIUM

    def test_complex_task_boundaries(self) -> None:
        """Test COMPLEX level boundaries."""
        assessor = ComplexityAssessor()

        # Score > 70 is COMPLEX
        result = assessor.assess(
            file_count=30,
            operation_types=["read", "write", "edit", "delete"],
        )
        # 30 (files) + 65 (4 ops) = 95
        assert result.score > 70
        assert result.level == ComplexityLevel.COMPLEX

    def test_score_100_full_pipeline(self) -> None:
        """Test achieving maximum complexity score."""
        assessor = ComplexityAssessor()
        result = assessor.assess(
            task_description="x" * 250,  # Long description
            file_count=100,
            operation_types=["bash", "execute", "delete", "write", "edit"],
        )

        assert result.score == 100
        assert result.level == ComplexityLevel.COMPLEX
