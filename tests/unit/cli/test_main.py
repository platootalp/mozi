"""Unit tests for the CLI main module.

Tests cover:
- Typer application creation
- Version command
- Output formatting
- Error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.cli.commands import (
    CLIError,
    OrchestratorFactory,
    execute_task,
    execute_task_with_retry,
)
from mozi.cli.output import OutputFormat, OutputFormatter
from mozi.orchestrator.orchestrator import OrchestratorResult


class TestOutputFormatter:
    """Tests for OutputFormatter class."""

    def test_formatter_initialization(self) -> None:
        """Test output formatter initializes correctly."""
        formatter = OutputFormatter()

        assert formatter.output_format == OutputFormat.RICH
        assert formatter.console is not None

    def test_formatter_with_simple_format(self) -> None:
        """Test output formatter with simple format."""
        formatter = OutputFormatter(format=OutputFormat.SIMPLE)

        assert formatter.output_format == OutputFormat.SIMPLE

    def test_formatter_with_json_format(self) -> None:
        """Test output formatter with JSON format."""
        formatter = OutputFormatter(format=OutputFormat.JSON)

        assert formatter.output_format == OutputFormat.JSON

    def test_formatter_no_color(self) -> None:
        """Test output formatter with no color."""
        formatter = OutputFormatter(no_color=True)

        assert formatter.console is not None

    def test_format_result_simple(self) -> None:
        """Test formatting result in simple mode."""
        formatter = OutputFormatter(format=OutputFormat.SIMPLE)

        mock_result = MagicMock()
        mock_result.content = "Test result"
        mock_result.to_dict = MagicMock(return_value={})

        formatted = formatter.format_result(mock_result)
        assert "Test result" in formatted

    def test_format_result_json(self) -> None:
        """Test formatting result in JSON mode."""
        formatter = OutputFormatter(format=OutputFormat.JSON)

        mock_result = MagicMock()
        mock_result.content = "Test result"
        mock_result.to_dict = MagicMock(
            return_value={"success": True, "content": "Test result"}
        )

        formatted = formatter.format_result(mock_result)
        assert '"success": true' in formatted

    def test_format_error_simple(self) -> None:
        """Test formatting error in simple mode."""
        formatter = OutputFormatter(format=OutputFormat.SIMPLE)

        error = ValueError("Test error")
        formatted = formatter.format_error(error)

        assert "Test error" in formatted

    def test_format_error_json(self) -> None:
        """Test formatting error in JSON mode."""
        formatter = OutputFormatter(format=OutputFormat.JSON)

        error = ValueError("Test error")
        formatted = formatter.format_error(error)

        assert '"error": "ValueError"' in formatted
        assert '"message": "Test error"' in formatted

    def test_format_error_with_cause(self) -> None:
        """Test formatting error with cause."""
        formatter = OutputFormatter(format=OutputFormat.JSON)

        cause = ValueError("Original error")
        error = CLIError("Wrapper error", cause=cause)

        formatted = formatter.format_error(error)
        assert '"cause": "Original error"' in formatted

    def test_print_info(self) -> None:
        """Test printing info message."""
        formatter = OutputFormatter()

        # Should not raise
        formatter.print_info("Test info message")

    def test_print_warning(self) -> None:
        """Test printing warning message."""
        formatter = OutputFormatter()

        # Should not raise
        formatter.print_warning("Test warning message")

    def test_print_success(self) -> None:
        """Test printing success message."""
        formatter = OutputFormatter()

        # Should not raise
        formatter.print_success("Test success message")


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self) -> None:
        """Test OutputFormat enum values."""
        assert OutputFormat.SIMPLE.value == "simple"
        assert OutputFormat.DETAILED.value == "detailed"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.RICH.value == "rich"


class TestOrchestratorFactory:
    """Tests for OrchestratorFactory class."""

    def teardown_method(self) -> None:
        """Reset orchestrator after each test."""
        OrchestratorFactory.reset()

    def test_get_orchestrator_creates_instance(self) -> None:
        """Test that get_orchestrator creates an instance."""
        mock_adapter = MagicMock()
        mock_registry = MagicMock()

        orchestrator = OrchestratorFactory.get_orchestrator(
            model_adapter=mock_adapter,
            tool_registry=mock_registry,
        )

        assert orchestrator is not None

    def test_get_orchestrator_returns_same_instance(self) -> None:
        """Test that get_orchestrator returns the same instance."""
        mock_adapter = MagicMock()

        orch1 = OrchestratorFactory.get_orchestrator(model_adapter=mock_adapter)
        orch2 = OrchestratorFactory.get_orchestrator(model_adapter=mock_adapter)

        assert orch1 is orch2

    def test_reset_clears_instance(self) -> None:
        """Test that reset clears the orchestrator instance."""
        mock_adapter = MagicMock()

        orch1 = OrchestratorFactory.get_orchestrator(model_adapter=mock_adapter)
        OrchestratorFactory.reset()
        orch2 = OrchestratorFactory.get_orchestrator(model_adapter=mock_adapter)

        assert orch1 is not orch2


class TestExecuteTask:
    """Tests for execute_task function."""

    @pytest.mark.asyncio
    async def test_execute_task_success(self) -> None:
        """Test successful task execution."""
        mock_result = MagicMock(spec=OrchestratorResult)
        mock_result.success = True
        mock_result.session_id = "sess_test123"
        mock_result.content = "Task completed"

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=mock_orchestrator,
        ):
            result = await execute_task("Test task")

            assert result.success is True
            assert result.content == "Task completed"
            mock_orchestrator.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_with_session(self) -> None:
        """Test task execution with existing session."""
        mock_result = MagicMock(spec=OrchestratorResult)
        mock_result.success = True
        mock_result.session_id = "sess_existing"

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=mock_orchestrator,
        ):
            result = await execute_task(
                "Test task",
                session_id="sess_existing",
            )

            mock_orchestrator.execute.assert_called_once_with(
                task_description="Test task",
                session_id="sess_existing",
            )

    @pytest.mark.asyncio
    async def test_execute_task_orchestrator_error(self) -> None:
        """Test execute_task handles orchestrator errors."""
        from mozi.orchestrator.orchestrator import OrchestratorError

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(
            side_effect=OrchestratorError("Task failed")
        )

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=mock_orchestrator,
        ):
            with pytest.raises(CLIError) as exc_info:
                await execute_task("Test task")

            assert "Task failed" in str(exc_info.value)
            assert exc_info.value.command == "execute"


class TestExecuteTaskWithRetry:
    """Tests for execute_task_with_retry function."""

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self) -> None:
        """Test successful task execution with retry."""
        mock_result = MagicMock(spec=OrchestratorResult)
        mock_result.success = True
        mock_result.session_id = "sess_test123"

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute_with_retry = AsyncMock(return_value=mock_result)

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=mock_orchestrator,
        ):
            result = await execute_task_with_retry(
                "Test task",
                max_retries=3,
            )

            assert result.success is True
            mock_orchestrator.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_failure(self) -> None:
        """Test task execution with retry failure."""
        from mozi.orchestrator.orchestrator import OrchestratorError

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute_with_retry = AsyncMock(
            side_effect=OrchestratorError("All retries failed")
        )

        with patch.object(
            OrchestratorFactory,
            "get_orchestrator",
            return_value=mock_orchestrator,
        ):
            with pytest.raises(CLIError) as exc_info:
                await execute_task_with_retry(
                    "Test task",
                    max_retries=3,
                )

            assert "All retries failed" in str(exc_info.value)
            assert exc_info.value.command == "execute_with_retry"


class TestCLIError:
    """Tests for CLIError exception."""

    def test_cli_error_creation(self) -> None:
        """Test CLIError creation with message."""
        error = CLIError("Test error message")

        assert error.message == "Test error message"
        assert error.command is None
        assert error.cause is None

    def test_cli_error_with_command(self) -> None:
        """Test CLIError creation with command."""
        error = CLIError("Test error", command="execute")

        assert error.message == "Test error"
        assert error.command == "execute"

    def test_cli_error_with_cause(self) -> None:
        """Test CLIError creation with cause."""
        cause = ValueError("Original error")
        error = CLIError("Wrapper error", cause=cause)

        assert error.message == "Wrapper error"
        assert error.cause is cause

    def test_cli_error_repr(self) -> None:
        """Test CLIError string representation."""
        error = CLIError("Test error", command="execute")

        repr_str = repr(error)
        assert "CLIError" in repr_str
        assert "Test error" in repr_str

    def test_cli_error_command(self) -> None:
        """Test CLIError command attribute."""
        error = CLIError("Test error", command="execute")

        assert error.command == "execute"
        assert error.message == "Test error"


class TestMainApp:
    """Tests for main Typer application."""

    def test_app_import(self) -> None:
        """Test that app can be imported."""
        from mozi.cli.main import app

        assert app is not None
