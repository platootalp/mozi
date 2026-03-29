"""Main CLI application for Mozi AI Coding Agent.

This module provides the main Typer application with commands for
task execution, session management, and interactive mode.

Examples
--------
Run the CLI:

    $ mozi --help

Execute a task:

    $ mozi "Read the main.py file"

Start interactive mode:

    $ mozi --interactive
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from mozi import __version__
from mozi.cli.commands import (
    CLIError,
    continue_last_session,
    create_named_session,
    delete_session,
    execute_task,
    execute_task_with_retry,
    get_session,
    interactive_mode,
    list_sessions,
    resume_session_by_name_or_id,
)
from mozi.cli.output import OutputFormat, OutputFormatter
from mozi.core import MoziError

app = typer.Typer(
    name="mozi",
    help="Mozi AI Coding Agent - Build More, Waste Less",
    add_completion=False,
    no_args_is_help=True,
)

# Output formatter instance
_formatter: OutputFormatter | None = None


def get_formatter(
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "rich",
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color output")] = False,
) -> OutputFormatter:
    """Get or create the output formatter.

    Parameters
    ----------
    format : str, optional
        Output format (simple, detailed, json, rich). Defaults to "rich".
    no_color : bool, optional
        Disable color output. Defaults to False.

    Returns
    -------
    OutputFormatter
        The output formatter instance.
    """
    global _formatter
    if _formatter is None:
        try:
            output_format = OutputFormat(format.lower())
        except ValueError:
            output_format = OutputFormat.RICH
        _formatter = OutputFormatter(format=output_format, no_color=no_color)
    return _formatter


@app.command()
def main(
    ctx: typer.Context,
    task: Annotated[
        str | None,
        typer.Argument(help="Task description to execute"),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Start interactive mode"),
    ] = False,
    session: Annotated[
        str | None,
        typer.Option("--session", "-s", help="Session ID to resume"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
    retry: Annotated[
        bool,
        typer.Option("--retry", help="Enable automatic retry on failure"),
    ] = False,
    max_retries: Annotated[
        int,
        typer.Option("--max-retries", help="Maximum retry attempts"),
    ] = 3,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (simple, detailed, json, rich)"),
    ] = "rich",
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output"),
    ] = False,
    continue_last: Annotated[
        bool,
        typer.Option("--continue", "-c", help="Continue the most recent session"),
    ] = False,
    resume: Annotated[
        str | None,
        typer.Option("--resume", "-r", help="Resume session by name or ID"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Name for new session"),
    ] = None,
    print_mode: Annotated[
        bool,
        typer.Option("--print", "-p", help="Print result only (non-interactive)"),
    ] = False,
) -> None:
    """Execute a task or start interactive mode.

    If a task is provided, it will be executed through the orchestrator.
    If --interactive is set, enters interactive mode.

    Examples
    --------
    Execute a task:

        mozi "Read the main.py file"

    Start interactive mode:

        mozi --interactive

    Execute with specific session:

        mozi "Continue editing" --session sess_abc123
    """
    # When print_mode is True, use simple format for cleaner output
    output_format = format if not print_mode else "simple"
    formatter = get_formatter(format=output_format, no_color=no_color)

    try:
        # Handle new CLI flags for session management
        if continue_last:
            if task is None:
                raise CLIError("Task description required when using --continue")
            result = asyncio.run(
                continue_last_session(
                    task=task,
                    verbose=verbose,
                )
            )
            formatter.print_result(result)
            raise typer.Exit(code=0 if result.success else 1)

        if resume is not None:
            if task is None:
                raise CLIError("Task description required when using --resume")
            result = asyncio.run(
                resume_session_by_name_or_id(
                    name_or_id=resume,
                    task=task,
                    verbose=verbose,
                )
            )
            formatter.print_result(result)
            raise typer.Exit(code=0 if result.success else 1)

        if name is not None:
            if task is None:
                raise CLIError("Task description required when using --name")
            result = asyncio.run(
                create_named_session(
                    name=name,
                    task=task,
                    verbose=verbose,
                )
            )
            formatter.print_result(result)
            raise typer.Exit(code=0 if result.success else 1)

        if interactive or task is None:
            # Interactive mode
            output_format = (
                OutputFormat.RICH if format.lower() == "detailed" else OutputFormat(format.lower())
            )
            asyncio.run(interactive_mode(verbose=verbose, output_format=output_format))
        else:
            # Execute single task
            if retry:
                result = asyncio.run(
                    execute_task_with_retry(
                        task_description=task,
                        max_retries=max_retries,
                        session_id=session,
                        verbose=verbose,
                    )
                )
            else:
                result = asyncio.run(
                    execute_task(
                        task_description=task,
                        session_id=session,
                        verbose=verbose,
                    )
                )

            formatter.print_result(result)

            # Exit with appropriate code
            raise typer.Exit(code=0 if result.success else 1)

    except CLIError as e:
        formatter.print_error(e)
        raise typer.Exit(code=1) from e

    except MoziError as e:
        formatter.print_error(e)
        raise typer.Exit(code=1) from e

    except Exception as e:
        formatter.print_error(e)
        raise typer.Exit(code=1) from e


@app.command()
def session_list(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of sessions to list"),
    ] = 10,
    offset: Annotated[
        int,
        typer.Option("--offset", "-o", help="Number of sessions to skip"),
    ] = 0,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format"),
    ] = "rich",
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output"),
    ] = False,
) -> None:
    """List recent sessions.

    Examples
    --------
    List recent sessions:

        mozi sessions

    List first 20 sessions:

        mozi sessions --limit 20
    """
    formatter = get_formatter(format=format, no_color=no_color)

    try:
        sessions = asyncio.run(list_sessions(limit=limit, offset=offset))

        if not sessions:
            formatter.print_info("No sessions found")
            return

        formatter.print_info(f"Sessions (total: {len(sessions)}):")
        for sess in sessions:
            sess_id = sess.get("session_id", "unknown")
            state = sess.get("state", "unknown")
            level = sess.get("complexity_level", "unknown")
            created = sess.get("created_at", "unknown")
            formatter.print_info(f"  {sess_id} | {state} | {level} | {created}")

    except Exception as e:
        formatter.print_error(e)
        raise typer.Exit(code=1) from e


@app.command()
def session_show(
    session_id: Annotated[
        str,
        typer.Argument(help="Session ID to show"),
    ],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format"),
    ] = "rich",
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output"),
    ] = False,
) -> None:
    """Show details of a session.

    Examples
    --------
    Show session details:

        mozi session sess_abc123
    """
    formatter = get_formatter(format=format, no_color=no_color)

    try:
        session = asyncio.run(get_session(session_id))

        if session is None:
            formatter.print_warning(f"Session not found: {session_id}")
            raise typer.Exit(code=1)

        formatted = formatter.format_session_info(session)
        print(formatted)

    except Exception as e:
        formatter.print_error(e)
        raise typer.Exit(code=1) from e


@app.command()
def session_delete(
    session_id: Annotated[
        str,
        typer.Argument(help="Session ID to delete"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format"),
    ] = "rich",
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output"),
    ] = False,
) -> None:
    """Delete a session.

    Examples
    --------
    Delete a session:

        mozi session-delete sess_abc123

    Force delete without confirmation:

        mozi session-delete sess_abc123 --force
    """
    formatter = get_formatter(format=format, no_color=no_color)

    try:
        if not force:
            confirm = typer.confirm(f"Delete session {session_id}?")
            if not confirm:
                formatter.print_info("Deletion cancelled")
                return

        success = asyncio.run(delete_session(session_id))

        if success:
            formatter.print_success(f"Session deleted: {session_id}")
        else:
            formatter.print_warning(f"Session not found or could not be deleted: {session_id}")
            raise typer.Exit(code=1)

    except Exception as e:
        formatter.print_error(e)
        raise typer.Exit(code=1) from e


@app.command()
def version() -> None:
    """Show version information.

    Examples
    --------
    Show version:

        mozi version
    """
    print(f"Mozi AI Coding Agent v{__version__}")


def run() -> None:
    """Run the CLI application.

    This is the main entry point for the mozi command.
    """
    app()


if __name__ == "__main__":
    run()
