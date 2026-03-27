"""Output formatting for CLI results.

This module provides output formatting utilities for displaying
orchestrator results, errors, and status information in the CLI.

Examples
--------
Format a successful result:

    output = format_result(result)
    print(output)

Format an error:

    output = format_error(error)
    print(output)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class OutputFormat(StrEnum):
    """Output format types for CLI display."""

    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    RICH = "rich"


class OutputFormatter:
    """Formatter for CLI output.

    This class handles formatting of orchestrator results,
    errors, and status information for display in the terminal.

    Attributes
    ----------
    console : Console
        Rich console for colored output.
    format : OutputFormat
        Current output format.
    """

    def __init__(
        self,
        format: OutputFormat = OutputFormat.RICH,
        no_color: bool = False,
    ) -> None:
        """Initialize the output formatter.

        Parameters
        ----------
        format : OutputFormat, optional
            Output format to use. Defaults to OutputFormat.RICH.
        no_color : bool, optional
            Disable color output. Defaults to False.
        """
        self._format = format
        self._console = Console(no_color=no_color)

    @property
    def console(self) -> Console:
        """Get the rich console instance.

        Returns
        -------
        Console
            The rich console for output.
        """
        return self._console

    @property
    def output_format(self) -> OutputFormat:
        """Get the current output format.

        Returns
        -------
        OutputFormat
            The current output format.
        """
        return self._format

    def format_result(self, result: Any) -> str:
        """Format an orchestrator result for display.

        Parameters
        ----------
        result : Any
            The orchestrator result to format.

        Returns
        -------
        str
            Formatted result string.
        """
        if self._format == OutputFormat.JSON:
            import json

            if hasattr(result, "to_dict"):
                return json.dumps(result.to_dict(), indent=2)
            return json.dumps(result, indent=2, default=str)

        if self._format == OutputFormat.SIMPLE:
            if hasattr(result, "content"):
                return str(result.content)
            return str(result)

        # RICH format
        return self._format_rich_result(result)

    def _format_rich_result(self, result: Any) -> str:
        """Format result using rich library.

        Parameters
        ----------
        result : Any
            The result to format.

        Returns
        -------
        str
            Formatted string representation.
        """
        output_lines: list[str] = []

        if hasattr(result, "success"):
            status = "[green]SUCCESS[/green]" if result.success else "[red]FAILED[/red]"
            output_lines.append(f"Status: {status}")

        if hasattr(result, "session_id") and result.session_id:
            output_lines.append(f"Session: {result.session_id}")

        if hasattr(result, "complexity") and result.complexity:
            level = (
                result.complexity.level.value
                if hasattr(result.complexity.level, "value")
                else result.complexity.level
            )
            score = (
                result.complexity.score
                if hasattr(result.complexity, "score")
                else "N/A"
            )
            output_lines.append(f"Complexity: {level} (score: {score})")

        if hasattr(result, "routing") and result.routing:
            strategy = (
                result.routing.strategy.value
                if hasattr(result.routing.strategy, "value")
                else result.routing.strategy
            )
            output_lines.append(f"Strategy: {strategy}")

        if hasattr(result, "execution_time_ms"):
            output_lines.append(f"Execution time: {result.execution_time_ms}ms")

        if hasattr(result, "content") and result.content:
            output_lines.append("")
            output_lines.append("Result:")
            output_lines.append(result.content)

        if hasattr(result, "error") and result.error:
            output_lines.append("")
            output_lines.append(f"[red]Error:[/red] {result.error}")

        return "\n".join(output_lines)

    def format_error(self, error: Exception) -> str:
        """Format an error for display.

        Parameters
        ----------
        error : Exception
            The error to format.

        Returns
        -------
        str
            Formatted error string.
        """
        if self._format == OutputFormat.JSON:
            import json

            error_dict = {
                "error": type(error).__name__,
                "message": str(error),
            }
            if hasattr(error, "cause") and error.cause:
                error_dict["cause"] = str(error.cause)
            return json.dumps(error_dict, indent=2)

        if self._format == OutputFormat.SIMPLE:
            return f"Error: {error}"

        # RICH format
        error_type = type(error).__name__
        error_msg = str(error)


        panel = Panel(
            f"[red]{error_msg}[/red]",
            title=f"[bold red]{error_type}[/bold red]",
            border_style="red",
        )
        from io import StringIO

        from rich.console import Console

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)
        console.print(panel)
        return string_io.getvalue()

    def format_session_info(self, session: Any) -> str:
        """Format session information for display.

        Parameters
        ----------
        session : Any
            The session context to format.

        Returns
        -------
        str
            Formatted session information.
        """
        if self._format == OutputFormat.JSON:
            import json

            if hasattr(session, "to_dict"):
                return json.dumps(session.to_dict(), indent=2)
            return json.dumps(session, indent=2, default=str)

        # RICH format

        table = Table(title="Session Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        if hasattr(session, "session_id"):
            table.add_row("Session ID", session.session_id)

        if hasattr(session, "state"):
            state = (
                session.state.value
                if hasattr(session.state, "value")
                else str(session.state)
            )
            table.add_row("State", state)

        if hasattr(session, "complexity_level"):
            level = (
                session.complexity_level.value
                if hasattr(session.complexity_level, "value")
                else str(session.complexity_level)
            )
            table.add_row("Complexity Level", level)

        if hasattr(session, "complexity_score"):
            table.add_row("Complexity Score", str(session.complexity_score))

        if hasattr(session, "created_at"):
            created = (
                session.created_at.isoformat()
                if hasattr(session.created_at, "isoformat")
                else str(session.created_at)
            )
            table.add_row("Created At", created)

        from io import StringIO

        from rich.console import Console

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)
        console.print(table)
        return string_io.getvalue()

    def print_result(self, result: Any) -> None:
        """Print a formatted result to the console.

        Parameters
        ----------
        result : Any
            The result to print.
        """
        formatted = self.format_result(result)
        if self._format == OutputFormat.RICH:
            self._console.print(formatted)
        else:
            print(formatted)

    def print_error(self, error: Exception) -> None:
        """Print a formatted error to the console.

        Parameters
        ----------
        error : Exception
            The error to print.
        """
        formatted = self.format_error(error)
        if self._format == OutputFormat.RICH:
            self._console.print(formatted)
        else:
            print(formatted, file=__import__("sys").stderr)

    def print_info(self, message: str) -> None:
        """Print an info message to the console.

        Parameters
        ----------
        message : str
            The info message to print.
        """
        if self._format == OutputFormat.RICH:
            self._console.print(f"[blue]{message}[/blue]")
        else:
            print(message)

    def print_warning(self, message: str) -> None:
        """Print a warning message to the console.

        Parameters
        ----------
        message : str
            The warning message to print.
        """
        if self._format == OutputFormat.RICH:
            self._console.print(f"[yellow]Warning:[/yellow] {message}")
        else:
            print(f"Warning: {message}")

    def print_success(self, message: str) -> None:
        """Print a success message to the console.

        Parameters
        ----------
        message : str
            The success message to print.
        """
        if self._format == OutputFormat.RICH:
            self._console.print(f"[green]{message}[/green]")
        else:
            print(message)


def format_result(result: Any) -> str:
    """Format an orchestrator result for display.

    Parameters
    ----------
    result : Any
        The orchestrator result to format.

    Returns
    -------
    str
        Formatted result string.
    """
    formatter = OutputFormatter()
    return formatter.format_result(result)


def format_error(error: Exception) -> str:
    """Format an error for display.

    Parameters
    ----------
    error : Exception
        The error to format.

    Returns
    -------
    str
        Formatted error string.
    """
    formatter = OutputFormatter()
    return formatter.format_error(error)
