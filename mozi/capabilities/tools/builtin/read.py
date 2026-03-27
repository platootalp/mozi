"""Read file tool for Mozi AI Coding Agent.

This module provides the ReadFileTool for reading file contents.

Examples
--------
Read a file:

    tool = ReadFileTool()
    result = await tool.execute(context, path="test.py")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult


class ReadFileTool(Tool):
    """Tool for reading file contents.

    This tool reads the contents of a file from the filesystem.
    It supports reading from the working directory or absolute paths.

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
    Read a file:

        tool = ReadFileTool()
        result = await tool.execute(context, path="README.md")

    Read with absolute path:

        result = await tool.execute(context, path="/absolute/path/to/file")
    """

    name: str = "read_file"
    description: str = "Read contents of a file"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read",
                "default": None,
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-indexed)",
                "default": 0,
            },
        },
        "required": ["path"],
    }

    async def execute(  # type: ignore[override]
        self,
        context: ToolContext,
        path: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> ToolResult:
        """Read file contents.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        path : str
            Path to the file to read.
        limit : int | None, optional
            Maximum number of lines to read.
        offset : int, optional
            Line number to start reading from (0-indexed).

        Returns
        -------
        ToolResult
            The result containing file contents or error.
        """
        try:
            file_path = self._resolve_path(context, path)

            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {path}",
                )

            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a file: {path}",
                )

            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if offset > 0:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]

            output_lines = "\n".join(lines)

            return ToolResult(
                success=True,
                output=output_lines,
                metadata={
                    "path": str(file_path),
                    "lines": len(lines),
                    "total_lines": len(content.splitlines()),
                },
            )

        except PermissionError:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {path}",
            )
        except OSError:
            return ToolResult(
                success=False,
                output=None,
                error="Error reading file",
            )

    def _resolve_path(self, context: ToolContext, path: str) -> Path:
        """Resolve a file path relative to the working directory.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        path : str
            The path to resolve.

        Returns
        -------
        Path
            The resolved absolute path.
        """
        if os.path.isabs(path):
            return Path(path)
        return Path(context.working_directory) / path
