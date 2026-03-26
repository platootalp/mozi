"""Tests for mozi.core.error module.

This module contains unit tests for all Mozi exception classes.
"""

from __future__ import annotations

import pytest

from mozi.core.error import (
    MoziConfigError,
    MoziError,
    MoziRuntimeError,
    MoziSessionError,
    MoziToolError,
)


class TestMoziError:
    """Tests for MoziError base exception class."""

    def test_raise_with_message(self) -> None:
        """Test raising MoziError with only a message."""
        with pytest.raises(MoziError) as exc_info:
            raise MoziError("Test error message")

        assert exc_info.value.message == "Test error message"
        assert str(exc_info.value) == "Test error message"
        assert exc_info.value.cause is None

    def test_raise_with_message_and_cause(self) -> None:
        """Test raising MoziError with message and cause."""
        original_error = ValueError("Original error")
        with pytest.raises(MoziError) as exc_info:
            raise MoziError("Wrapper error", cause=original_error)

        assert exc_info.value.message == "Wrapper error"
        assert exc_info.value.cause is original_error

    def test_raise_with_cause_via_from(self) -> None:
        """Test raising MoziError with cause via 'from' syntax.

        The 'from' keyword sets __cause__ but not our custom cause attribute.
        Use the cause parameter for explicit chaining.
        """
        original_error = RuntimeError("Original error")
        with pytest.raises(MoziError) as exc_info:
            raise MoziError("Wrapper error") from original_error

        # __cause__ is set by 'raise ... from' syntax
        assert exc_info.value.__cause__ is original_error
        # but our custom cause attribute is not automatically set
        assert exc_info.value.cause is None

    def test_str_representation(self) -> None:
        """Test string representation of MoziError."""
        error = MoziError("test message")
        assert str(error) == "test message"

    def test_repr_without_cause(self) -> None:
        """Test repr without cause."""
        error = MoziError("test message")
        assert repr(error) == "MoziError(message='test message', cause=None)"

    def test_repr_with_cause(self) -> None:
        """Test repr with cause."""
        original_error = ValueError("cause error")
        error = MoziError("test message", cause=original_error)
        assert repr(error) == "MoziError(message='test message', cause=ValueError('cause error'))"

    def test_inheritance(self) -> None:
        """Test that MoziError inherits from Exception."""
        error = MoziError("test")
        assert isinstance(error, Exception)
        assert isinstance(error, MoziError)


class TestMoziConfigError:
    """Tests for MoziConfigError exception class."""

    def test_raise_with_message(self) -> None:
        """Test raising MoziConfigError with only a message."""
        with pytest.raises(MoziConfigError) as exc_info:
            raise MoziConfigError("Invalid configuration")

        assert exc_info.value.message == "Invalid configuration"

    def test_raise_with_cause(self) -> None:
        """Test raising MoziConfigError with cause."""
        original_error = ValueError("Invalid value")
        with pytest.raises(MoziConfigError) as exc_info:
            raise MoziConfigError("Config error", cause=original_error)

        assert exc_info.value.cause is original_error

    def test_inheritance(self) -> None:
        """Test that MoziConfigError inherits from MoziError."""
        error = MoziConfigError("test")
        assert isinstance(error, MoziError)
        assert isinstance(error, Exception)


class TestMoziRuntimeError:
    """Tests for MoziRuntimeError exception class."""

    def test_raise_with_message(self) -> None:
        """Test raising MoziRuntimeError with only a message."""
        with pytest.raises(MoziRuntimeError) as exc_info:
            raise MoziRuntimeError("Runtime error occurred")

        assert exc_info.value.message == "Runtime error occurred"

    def test_raise_with_cause(self) -> None:
        """Test raising MoziRuntimeError with cause."""
        original_error = TimeoutError("Operation timed out")
        with pytest.raises(MoziRuntimeError) as exc_info:
            raise MoziRuntimeError("Runtime error", cause=original_error)

        assert exc_info.value.cause is original_error

    def test_inheritance(self) -> None:
        """Test that MoziRuntimeError inherits from MoziError."""
        error = MoziRuntimeError("test")
        assert isinstance(error, MoziError)
        assert isinstance(error, Exception)


class TestMoziToolError:
    """Tests for MoziToolError exception class."""

    def test_raise_with_message_only(self) -> None:
        """Test raising MoziToolError with only a message."""
        with pytest.raises(MoziToolError) as exc_info:
            raise MoziToolError("Tool execution failed")

        assert exc_info.value.message == "Tool execution failed"
        assert exc_info.value.tool_name is None

    def test_raise_with_tool_name(self) -> None:
        """Test raising MoziToolError with tool name."""
        with pytest.raises(MoziToolError) as exc_info:
            raise MoziToolError("Tool failed", tool_name="bash")

        assert exc_info.value.message == "Tool failed"
        assert exc_info.value.tool_name == "bash"

    def test_raise_with_all_parameters(self) -> None:
        """Test raising MoziToolError with all parameters."""
        original_error = PermissionError("Permission denied")
        with pytest.raises(MoziToolError) as exc_info:
            raise MoziToolError(
                "Tool 'bash' execution failed",
                tool_name="bash",
                cause=original_error,
            )

        assert exc_info.value.message == "Tool 'bash' execution failed"
        assert exc_info.value.tool_name == "bash"
        assert exc_info.value.cause is original_error

    def test_repr_with_tool_name(self) -> None:
        """Test repr includes tool_name."""
        error = MoziToolError("test error", tool_name="read_file")
        assert "tool_name='read_file'" in repr(error)

    def test_inheritance(self) -> None:
        """Test that MoziToolError inherits from MoziError."""
        error = MoziToolError("test")
        assert isinstance(error, MoziError)
        assert isinstance(error, Exception)


class TestMoziSessionError:
    """Tests for MoziSessionError exception class."""

    def test_raise_with_message_only(self) -> None:
        """Test raising MoziSessionError with only a message."""
        with pytest.raises(MoziSessionError) as exc_info:
            raise MoziSessionError("Session error")

        assert exc_info.value.message == "Session error"
        assert exc_info.value.session_id is None

    def test_raise_with_session_id(self) -> None:
        """Test raising MoziSessionError with session ID."""
        with pytest.raises(MoziSessionError) as exc_info:
            raise MoziSessionError("Session not found", session_id="abc123")

        assert exc_info.value.message == "Session not found"
        assert exc_info.value.session_id == "abc123"

    def test_raise_with_all_parameters(self) -> None:
        """Test raising MoziSessionError with all parameters."""
        original_error = OSError("Session file corrupted")
        with pytest.raises(MoziSessionError) as exc_info:
            raise MoziSessionError(
                "Failed to restore session",
                session_id="xyz789",
                cause=original_error,
            )

        assert exc_info.value.message == "Failed to restore session"
        assert exc_info.value.session_id == "xyz789"
        assert exc_info.value.cause is original_error

    def test_repr_with_session_id(self) -> None:
        """Test repr includes session_id."""
        error = MoziSessionError("test error", session_id="session123")
        assert "session_id='session123'" in repr(error)

    def test_inheritance(self) -> None:
        """Test that MoziSessionError inherits from MoziError."""
        error = MoziSessionError("test")
        assert isinstance(error, MoziError)
        assert isinstance(error, Exception)


class TestExceptionChaining:
    """Tests for exception chaining behavior."""

    def test_mozi_error_chaining_with_from(self) -> None:
        """Test exception chaining using 'from' keyword."""
        original = ValueError("original error")
        with pytest.raises(MoziError) as exc_info:
            raise MoziError("new error") from original

        assert exc_info.value.__cause__ is original

    def test_mozi_error_preserves_cause_attribute(self) -> None:
        """Test that cause attribute is preserved."""
        original = RuntimeError("runtime error")
        error = MoziError("wrapper", cause=original)

        assert error.cause is original
        assert error.__cause__ is None  # __cause__ only set via 'from'

    def test_all_subclasses_support_cause(self) -> None:
        """Test all exception subclasses support cause parameter."""
        original = Exception("original")

        config_err = MoziConfigError("config", cause=original)
        assert config_err.cause is original

        runtime_err = MoziRuntimeError("runtime", cause=original)
        assert runtime_err.cause is original

        tool_err = MoziToolError("tool", cause=original)
        assert tool_err.cause is original

        session_err = MoziSessionError("session", cause=original)
        assert session_err.cause is original
