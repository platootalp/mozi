"""Core error classes for Mozi AI Coding Agent.

This module defines the exception hierarchy for the Mozi package.
All custom exceptions inherit from MoziError base class.

Examples
--------
Raise a configuration error:
    raise MoziConfigError("Invalid configuration value")

Catch a specific error type:
    try:
        ...
    except MoziToolError as e:
        ...
"""

from __future__ import annotations

__all__ = [
    "MoziError",
    "MoziConfigError",
    "MoziRuntimeError",
    "MoziToolError",
    "MoziSessionError",
]


class MoziError(Exception):
    """Base exception for all Mozi errors.

    All custom exceptions in the mozi package should inherit from this class.
    It provides a consistent interface for error handling across the codebase.

    Attributes
    ----------
    message : str
        Human-readable error message describing the error.
    cause : Exception | None
        The original exception that caused this error, if any.

    Examples
    --------
    Create a custom exception:

        class MyCustomError(MoziError):
            pass

        raise MyCustomError("Something went wrong") from ValueError("original error")
    """

    def __init__(
        self,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize MoziError with message and optional cause.

        Parameters
        ----------
        message : str
            Human-readable error message.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message)
        self.message: str = message
        self.cause: Exception | None = cause

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        cause_repr = repr(self.cause) if self.cause else None
        return f"{self.__class__.__name__}(message={self.message!r}, cause={cause_repr})"


class MoziConfigError(MoziError):
    """Exception raised for configuration-related errors.

    This exception is raised when there are issues with configuration files,
    environment variables, or invalid configuration values.

    Examples
    --------
    Raise when configuration file is missing:

        raise MoziConfigError("Configuration file not found: config.json")

    Raise when environment variable is invalid:

        raise MoziConfigError(
            "Invalid MOZI_LOG_LEVEL value",
            cause=ValueError("Log level must be DEBUG, INFO, WARNING, or ERROR")
        )
    """

    pass


class MoziRuntimeError(MoziError):
    """Exception raised for runtime errors during execution.

    This exception is raised when unexpected errors occur during
    the agent's operation, such as resource exhaustion, timeouts,
    or internal state errors.

    Examples
    --------
    Raise when operation times out:

        raise MoziRuntimeError("Operation timed out after 30 seconds")

    Raise when internal state is invalid:

        raise MoziRuntimeError(
            "Invalid orchestrator state",
            cause=RuntimeError("Expected state RUNNING, got IDLE")
        )
    """

    pass


class MoziToolError(MoziError):
    """Exception raised when a tool execution fails.

    This exception is raised when tool execution fails due to
    sandbox violations, tool not found, or tool execution errors.

    Attributes
    ----------
    tool_name : str | None
        The name of the tool that failed, if known.

    Examples
    --------
    Raise when tool execution fails:

        raise MoziToolError("Tool 'bash' execution failed: permission denied")

    Raise with tool name:

        raise MoziToolError(
            "Tool 'read_file' failed: file not found",
            cause=FileNotFoundError("config.json")
        )
    """

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize MoziToolError with tool name.

        Parameters
        ----------
        message : str
            Human-readable error message.
        tool_name : str | None, optional
            The name of the tool that failed.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.tool_name: str | None = tool_name

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        cause_repr = repr(self.cause) if self.cause else None
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"tool_name={self.tool_name!r}, "
            f"cause={cause_repr})"
        )


class MoziSessionError(MoziError):
    """Exception raised for session management errors.

    This exception is raised when there are issues with session
    creation, restoration, persistence, or invalid session state.

    Attributes
    ----------
    session_id : str | None
        The session ID involved in the error, if known.

    Examples
    --------
    Raise when session not found:

        raise MoziSessionError("Session not found: abc123")

    Raise when session restoration fails:

        raise MoziSessionError(
            "Failed to restore session",
            cause=IOError("Session file corrupted")
        )
    """

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize MoziSessionError with session ID.

        Parameters
        ----------
        message : str
            Human-readable error message.
        session_id : str | None, optional
            The session ID involved in the error.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.session_id: str | None = session_id

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        cause_repr = repr(self.cause) if self.cause else None
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"session_id={self.session_id!r}, "
            f"cause={cause_repr})"
        )
