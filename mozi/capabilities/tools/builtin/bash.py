"""Bash tool for Mozi AI Coding Agent.

This module provides the BashTool for executing bash commands.

Examples
--------
Execute a command:

    tool = BashTool()
    result = await tool.execute(context, command="ls -la")
"""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult


class BashTool(Tool):
    """Tool for executing bash commands.

    This tool executes bash commands in a subprocess and returns
    the output. It supports timeout and working directory configuration.

    Attributes
    ----------
    name : str
        The unique identifier for this tool.
    description : str
        Human-readable description of the tool.
    parameters : dict[str, Any]
        JSON schema for tool parameters.

    Examples
    --------
    Execute a simple command:

        tool = BashTool()
        result = await tool.execute(context, command="ls -la")

    Execute with timeout:

        result = await tool.execute(
            context,
            command="sleep 5 && echo done",
            timeout=10
        )
    """

    name: str = "bash"
    description: str = "Execute a bash command"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds",
                "default": 30,
            },
            "working_directory": {
                "type": "string",
                "description": "Working directory for command execution",
                "default": None,
            },
        },
        "required": ["command"],
    }

    async def execute(  # type: ignore[override]
        self,
        context: ToolContext,
        command: str,
        timeout: int = 30,
        working_directory: str | None = None,
    ) -> ToolResult:
        """Execute a bash command.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        command : str
            The bash command to execute.
        timeout : int, optional
            Maximum execution time in seconds.
        working_directory : str | None, optional
            Working directory for command execution.

        Returns
        -------
        ToolResult
            The result containing command output or error.
        """
        if timeout > context.timeout:
            timeout = context.timeout

        cwd = working_directory or context.working_directory

        if not os.path.isabs(cwd):
            cwd = os.path.join(context.working_directory, cwd)

        bash_path = shutil.which("bash")
        shell_path = bash_path or "/bin/sh"

        try:
            process = await asyncio.create_subprocess_exec(
                shell_path,
                "-c",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout = stdout_bytes.decode("utf-8") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8") if stderr_bytes else ""

            return ToolResult(
                success=process.returncode == 0,
                output={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": process.returncode,
                },
                error=None if process.returncode == 0 else stderr,
                metadata={
                    "command": command,
                    "cwd": cwd,
                    "timeout": timeout,
                },
            )

        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass

            return ToolResult(
                success=False,
                output=None,
                error=f"Command timed out after {timeout} seconds",
                metadata={"command": command, "timeout": timeout},
            )

        except OSError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to execute command: {e}",
                metadata={"command": command},
            )
