"""CLI commands implementation.

This module provides the command implementations for the Mozi CLI,
including task execution, session management, and interactive mode.

Examples
--------
Execute a task:

    result = await execute_task("Read the main.py file")

List sessions:

    sessions = await list_sessions()
"""

from __future__ import annotations

from typing import Any

from mozi.cli.output import OutputFormat, OutputFormatter
from mozi.core import MoziError
from mozi.orchestrator.orchestrator import (
    MainOrchestrator,
    OrchestratorError,
    OrchestratorResult,
)


class CLIError(MoziError):
    """Exception raised for CLI errors.

    This exception is raised when CLI operations fail,
    such as invalid input or orchestrator errors.

    Attributes
    ----------
    command : str | None
        The command that caused the error.
    """

    def __init__(
        self,
        message: str,
        command: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize CLIError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        command : str | None, optional
            The command that caused the error.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.command: str | None = command


class OrchestratorFactory:
    """Factory for creating and managing the orchestrator instance.

    This class provides a singleton-like pattern for creating
    and accessing the MainOrchestrator instance.

    Attributes
    ----------
    _orchestrator : MainOrchestrator | None
        The cached orchestrator instance.
    """

    _orchestrator: MainOrchestrator | None = None

    @classmethod
    def get_orchestrator(
        cls,
        model_adapter: Any = None,
        tool_registry: Any = None,
    ) -> MainOrchestrator:
        """Get or create the orchestrator instance.

        Parameters
        ----------
        model_adapter : Any, optional
            Model adapter for LLM interactions.
        tool_registry : Any, optional
            Tool registry for tool execution.

        Returns
        -------
        MainOrchestrator
            The orchestrator instance.
        """
        if cls._orchestrator is None:
            from mozi.infrastructure.model import AnthropicModelAdapter

            # Create a default model adapter if not provided
            if model_adapter is None:
                model_adapter = AnthropicModelAdapter(
                    api_key="dummy",  # Will be loaded from environment
                )

            cls._orchestrator = MainOrchestrator(
                model_adapter=model_adapter,
                tool_registry=tool_registry,
            )

        return cls._orchestrator

    @classmethod
    def reset(cls) -> None:
        """Reset the orchestrator instance.

        This is primarily useful for testing.
        """
        cls._orchestrator = None


async def execute_task(
    task_description: str,
    session_id: str | None = None,
    verbose: bool = False,
) -> OrchestratorResult:
    """Execute a task through the orchestrator.

    Parameters
    ----------
    task_description : str
        Natural language description of the task.
    session_id : str | None, optional
        Existing session ID to resume.
    verbose : bool, optional
        Enable verbose output. Defaults to False.

    Returns
    -------
    OrchestratorResult
        The result of the task execution.

    Raises
    ------
    CLIError
        If the task execution fails.
    """
    try:
        orchestrator = OrchestratorFactory.get_orchestrator()
        result = await orchestrator.execute(
            task_description=task_description,
            session_id=session_id,
        )
        return result

    except OrchestratorError as e:
        raise CLIError(
            f"Task execution failed: {e}",
            command="execute",
            cause=e,
        ) from e
    except Exception as e:
        raise CLIError(
            f"Unexpected error during task execution: {e}",
            command="execute",
            cause=e,
        ) from e


async def execute_task_with_retry(
    task_description: str,
    max_retries: int = 3,
    session_id: str | None = None,
    verbose: bool = False,
) -> OrchestratorResult:
    """Execute a task with automatic retry on failure.

    Parameters
    ----------
    task_description : str
        Natural language description of the task.
    max_retries : int, optional
        Maximum number of retry attempts. Defaults to 3.
    session_id : str | None, optional
        Existing session ID to resume.
    verbose : bool, optional
        Enable verbose output. Defaults to False.

    Returns
    -------
    OrchestratorResult
        The result of the task execution.

    Raises
    ------
    CLIError
        If all retry attempts fail.
    """
    try:
        orchestrator = OrchestratorFactory.get_orchestrator()
        result = await orchestrator.execute_with_retry(
            task_description=task_description,
            max_retries=max_retries,
            session_id=session_id,
        )
        return result

    except OrchestratorError as e:
        raise CLIError(
            f"Task execution failed after {max_retries} retries: {e}",
            command="execute_with_retry",
            cause=e,
        ) from e
    except Exception as e:
        raise CLIError(
            f"Unexpected error during task execution: {e}",
            command="execute_with_retry",
            cause=e,
        ) from e


async def list_sessions(
    limit: int = 10,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List recent sessions.

    Parameters
    ----------
    limit : int, optional
        Maximum number of sessions to return. Defaults to 10.
    offset : int, optional
        Number of sessions to skip. Defaults to 0.

    Returns
    -------
    list[dict[str, Any]]
        List of session dictionaries.
    """
    orchestrator = OrchestratorFactory.get_orchestrator()
    session_manager = orchestrator.get_session_manager()

    sessions = await session_manager.list_sessions()
    return [session.to_dict() for session in sessions]


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Get a session by ID.

    Parameters
    ----------
    session_id : str
        The session ID to retrieve.

    Returns
    -------
    dict[str, Any] | None
        Session dictionary or None if not found.
    """
    orchestrator = OrchestratorFactory.get_orchestrator()
    session_manager = orchestrator.get_session_manager()

    session = await session_manager.get_session(session_id)
    return session.to_dict() if session else None


async def delete_session(session_id: str) -> bool:
    """Delete a session.

    Parameters
    ----------
    session_id : str
        The session ID to delete.

    Returns
    -------
    bool
        True if deletion was successful.
    """
    orchestrator = OrchestratorFactory.get_orchestrator()
    session_manager = orchestrator.get_session_manager()

    await session_manager.delete_session(session_id)
    return True


async def interactive_mode(
    verbose: bool = False,
    output_format: OutputFormat = OutputFormat.RICH,
) -> None:
    """Run the CLI in interactive mode.

    This function provides an interactive REPL for the Mozi agent
    where users can continuously execute tasks.

    Parameters
    ----------
    verbose : bool, optional
        Enable verbose output. Defaults to False.
    output_format : OutputFormat, optional
        Output format to use. Defaults to OutputFormat.RICH.
    """
    formatter = OutputFormatter(format=output_format)

    formatter.print_info("Mozi AI Coding Agent - Interactive Mode")
    formatter.print_info("Type 'help' for commands, 'exit' to quit")
    formatter.print_info("")

    session_id: str | None = None

    while True:
        try:
            # Read input
            prompt = "mozi> " if not session_id else f"mozi [{session_id[:8]}]> "
            task_input = input(prompt).strip()

            if not task_input:
                continue

            # Handle built-in commands
            if task_input.lower() in ("exit", "quit", "q"):
                formatter.print_info("Goodbye!")
                break

            if task_input.lower() in ("help", "h", "?"):
                _print_interactive_help(formatter)
                continue

            if task_input.lower() == "clear":
                formatter.console.clear()
                continue

            if task_input.lower().startswith("session "):
                parts = task_input.split()
                if len(parts) >= 2:
                    session_id = parts[1]
                    formatter.print_info(f"Switched to session: {session_id}")
                else:
                    formatter.print_warning("Usage: session <session_id>")
                continue

            if task_input.lower() == "sessions":
                sessions = await list_sessions()
                formatter.print_info(f"Recent sessions: {len(sessions)}")
                for sess in sessions[:5]:
                    sess_id = sess.get("session_id", "unknown")
                    state = sess.get("state", "unknown")
                    formatter.print_info(f"  - {sess_id}: {state}")
                continue

            if task_input.lower() == "new":
                session_id = None
                formatter.print_info("Started new session")
                continue

            # Execute task
            formatter.print_info(f"Executing: {task_input}")

            result = await execute_task(
                task_description=task_input,
                session_id=session_id,
                verbose=verbose,
            )

            session_id = result.session_id

            # Print result
            formatter.print_result(result)

        except KeyboardInterrupt:
            formatter.print_info("")
            formatter.print_info("Use 'exit' to quit")
            continue

        except EOFError:
            formatter.print_info("")
            formatter.print_info("Goodbye!")
            break

        except CLIError as e:
            formatter.print_error(e)

        except MoziError as e:
            formatter.print_error(e)

        except Exception as e:
            formatter.print_error(e)


def _print_interactive_help(formatter: OutputFormatter) -> None:
    """Print help for interactive mode commands.

    Parameters
    ----------
    formatter : OutputFormatter
        The output formatter to use.
    """
    formatter.print_info("Interactive Mode Commands:")
    formatter.print_info("  help, h, ?  - Show this help message")
    formatter.print_info("  exit, quit, q - Exit interactive mode")
    formatter.print_info("  clear       - Clear the screen")
    formatter.print_info("  new         - Start a new session")
    formatter.print_info("  session <id> - Switch to an existing session")
    formatter.print_info("  sessions    - List recent sessions")
    formatter.print_info("")
    formatter.print_info("Any other input will be executed as a task")
