"""Tests for mozi.orchestrator.core.intent module.

This module contains unit tests for the intent recognition functionality.
"""

from __future__ import annotations

import pytest

from mozi.orchestrator.core.intent import (
    IntentRecognitionError,
    IntentResult,
    IntentScope,
    IntentType,
    recognize_intent,
)


class TestIntentType:
    """Tests for IntentType enum."""

    def test_all_intent_types_exist(self) -> None:
        """Test that all expected intent types are defined."""
        assert IntentType.CODE_EDIT.value == "CODE_EDIT"
        assert IntentType.CODE_READ.value == "CODE_READ"
        assert IntentType.BASH.value == "BASH"
        assert IntentType.ANALYSIS.value == "ANALYSIS"
        assert IntentType.UNKNOWN.value == "UNKNOWN"


class TestIntentScope:
    """Tests for IntentScope enum."""

    def test_all_intent_scopes_exist(self) -> None:
        """Test that all expected intent scopes are defined."""
        assert IntentScope.FILE.value == "FILE"
        assert IntentScope.PROJECT.value == "PROJECT"
        assert IntentScope.MULTIPLE.value == "MULTIPLE"
        assert IntentScope.UNKNOWN.value == "UNKNOWN"


class TestIntentResult:
    """Tests for IntentResult dataclass."""

    def test_create_intent_result(self) -> None:
        """Test creating an IntentResult instance."""
        result = IntentResult(
            task_type=IntentType.CODE_EDIT,
            scope=IntentScope.FILE,
            confidence=0.9,
            keywords=["edit", "file"],
            original_input="edit the main.py file",
        )

        assert result.task_type == IntentType.CODE_EDIT
        assert result.scope == IntentScope.FILE
        assert result.confidence == 0.9
        assert result.keywords == ["edit", "file"]
        assert result.original_input == "edit the main.py file"

    def test_to_dict(self) -> None:
        """Test converting IntentResult to dictionary."""
        result = IntentResult(
            task_type=IntentType.CODE_READ,
            scope=IntentScope.PROJECT,
            confidence=0.75,
            keywords=["find", "project"],
            original_input="find all python files in the project",
        )

        result_dict = result.to_dict()

        assert result_dict["task_type"] == "CODE_READ"
        assert result_dict["scope"] == "PROJECT"
        assert result_dict["confidence"] == 0.75
        assert result_dict["keywords"] == ["find", "project"]
        assert result_dict["original_input"] == "find all python files in the project"


class TestRecognizeIntentCodeEdit:
    """Tests for CODE_EDIT task type recognition."""

    @pytest.mark.parametrize(
        "input_text",
        [
            "edit the main.py file",
            "modify the function",
            "change the variable name",
            "update the configuration",
            "write a new test",
            "add a comment",
            "remove the unused import",
            "delete the temporary file",
            "replace foo with bar",
            "fix the bug",
            "implement the feature",
            "create a new module",
            "refactor the code",
        ],
    )
    def test_recognize_code_edit_keywords(self, input_text: str) -> None:
        """Test that code edit keywords are recognized."""
        result = recognize_intent(input_text)

        assert result.task_type == IntentType.CODE_EDIT
        assert result.original_input == input_text

    def test_recognize_code_edit_with_file_path(self) -> None:
        """Test recognizing code edit with a file path."""
        result = recognize_intent("edit /path/to/main.py")

        assert result.task_type == IntentType.CODE_EDIT
        assert result.scope == IntentScope.FILE


class TestRecognizeIntentCodeRead:
    """Tests for CODE_READ task type recognition."""

    @pytest.mark.parametrize(
        "input_text",
        [
            "read the file",
            "show me the content",
            "display the error",
            "find the function",
            "search for the keyword",
            "look at the code",
            "list the files",
            "get the configuration",
            "retrieve the data",
            "check the status",
            "view the log",
            "examine the structure",
            "cat the file",
        ],
    )
    def test_recognize_code_read_keywords(self, input_text: str) -> None:
        """Test that code read keywords are recognized."""
        result = recognize_intent(input_text)

        assert result.task_type == IntentType.CODE_READ
        assert result.original_input == input_text


class TestRecognizeIntentBash:
    """Tests for BASH task type recognition."""

    @pytest.mark.parametrize(
        "input_text",
        [
            "run the script",
            "execute the command",
            "run npm install",
            "pip install requirements",
            "python main.py",
            "node server.js",
            "make build",
            "build the project",
            "run the tests",
            "compile the code",
            "deploy to production",
            "start the server",
            "stop the service",
            "restart the daemon",
            "install the package",
            "uninstall the library",
        ],
    )
    def test_recognize_bash_keywords(self, input_text: str) -> None:
        """Test that bash keywords are recognized."""
        result = recognize_intent(input_text)

        assert result.task_type == IntentType.BASH
        assert result.original_input == input_text


class TestRecognizeIntentAnalysis:
    """Tests for ANALYSIS task type recognition."""

    @pytest.mark.parametrize(
        "input_text",
        [
            "analyze the codebase",
            "provide analysis of the issue",
            "review the code",
            "understand the structure",
            "explain how it works",
            "compare the approaches",
            "evaluate the performance",
            "assess the security",
            "create a report",
            "generate a summary",
            "diagnose the problem",
            "audit the logs",
            "trace the execution",
            "debug the issue",
            "profile the performance",
        ],
    )
    def test_recognize_analysis_keywords(self, input_text: str) -> None:
        """Test that analysis keywords are recognized."""
        result = recognize_intent(input_text)

        assert result.task_type == IntentType.ANALYSIS
        assert result.original_input == input_text


class TestRecognizeIntentScope:
    """Tests for intent scope recognition."""

    def test_recognize_file_scope(self) -> None:
        """Test recognizing file scope."""
        result = recognize_intent("edit main.py")

        assert result.scope == IntentScope.FILE

    def test_recognize_file_scope_with_path(self) -> None:
        """Test recognizing file scope with a path."""
        result = recognize_intent("edit /path/to/main.py")

        assert result.scope == IntentScope.FILE

    def test_recognize_project_scope(self) -> None:
        """Test recognizing project scope."""
        result = recognize_intent("analyze the entire codebase")

        assert result.scope == IntentScope.PROJECT

    def test_recognize_multiple_scope(self) -> None:
        """Test recognizing multiple scope."""
        result = recognize_intent("analyze all files in the project")

        assert result.scope == IntentScope.MULTIPLE

    def test_recognize_multiple_scope_with_multiple_files(self) -> None:
        """Test recognizing multiple scope with multiple files."""
        result = recognize_intent("edit file1.py file2.py file3.py")

        assert result.scope == IntentScope.MULTIPLE


class TestRecognizeIntentConfidence:
    """Tests for confidence scoring."""

    def test_higher_confidence_with_more_keywords(self) -> None:
        """Test that confidence increases with more keyword matches."""
        result_single = recognize_intent("edit")
        result_multiple = recognize_intent("edit modify change update")

        assert result_multiple.confidence > result_single.confidence

    def test_zero_confidence_for_unknown(self) -> None:
        """Test that unknown intents have zero confidence."""
        result = recognize_intent("asdfghjkl")

        assert result.confidence == 0.0


class TestRecognizeIntentEdgeCases:
    """Tests for edge cases in intent recognition."""

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises IntentRecognitionError."""
        with pytest.raises(IntentRecognitionError) as exc_info:
            recognize_intent("")

        assert "non-empty string" in str(exc_info.value).lower()

    def test_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only string raises IntentRecognitionError."""
        with pytest.raises(IntentRecognitionError) as exc_info:
            recognize_intent("   ")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_none_input_raises_error(self) -> None:
        """Test that None input raises IntentRecognitionError."""
        with pytest.raises(IntentRecognitionError):
            recognize_intent(None)  # type: ignore

    def test_case_insensitive_matching(self) -> None:
        """Test that keyword matching is case insensitive."""
        result_lower = recognize_intent("edit the file")
        result_upper = recognize_intent("EDIT the file")
        result_mixed = recognize_intent("EdIt the file")

        assert result_lower.task_type == result_upper.task_type
        assert result_upper.task_type == result_mixed.task_type

    def test_leading_trailing_whitespace_handled(self) -> None:
        """Test that leading and trailing whitespace is handled."""
        result = recognize_intent("  edit the file  ")

        assert result.task_type == IntentType.CODE_EDIT
        assert result.original_input == "  edit the file  "


class TestIntentRecognitionError:
    """Tests for IntentRecognitionError exception."""

    def test_raise_with_message(self) -> None:
        """Test raising IntentRecognitionError with a message."""
        with pytest.raises(IntentRecognitionError) as exc_info:
            raise IntentRecognitionError("Recognition failed")

        assert exc_info.value.message == "Recognition failed"

    def test_raise_with_cause(self) -> None:
        """Test raising IntentRecognitionError with a cause."""
        original_error = ValueError("Original error")
        with pytest.raises(IntentRecognitionError) as exc_info:
            raise IntentRecognitionError("Recognition failed", cause=original_error)

        assert exc_info.value.cause is original_error

    def test_inheritance(self) -> None:
        """Test that IntentRecognitionError inherits from MoziError."""
        error = IntentRecognitionError("test")

        from mozi.core.error import MoziError

        assert isinstance(error, MoziError)
        assert isinstance(error, Exception)


class TestIntegration:
    """Integration tests for intent recognition."""

    def test_full_example_code_edit(self) -> None:
        """Test a complete code edit example."""
        result = recognize_intent("edit the main.py file to fix the bug")

        assert result.task_type == IntentType.CODE_EDIT
        assert result.scope == IntentScope.FILE
        assert result.confidence > 0.0
        assert len(result.keywords) > 0

    def test_full_example_analysis(self) -> None:
        """Test a complete analysis example."""
        result = recognize_intent("analyze the entire project and create a report")

        assert result.task_type == IntentType.ANALYSIS
        assert result.scope == IntentScope.PROJECT
        assert result.confidence > 0.0

    def test_full_example_bash(self) -> None:
        """Test a complete bash example."""
        result = recognize_intent("run npm install to install dependencies")

        assert result.task_type == IntentType.BASH
        assert result.confidence > 0.0
