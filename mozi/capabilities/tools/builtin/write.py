"""Write file tool for Mozi AI Coding Agent.

This module provides the WriteFileTool for writing content to files.

Examples
--------
Write to a file:

    tool = WriteFileTool()
    result = await tool.execute(context, path="output.txt", content="Hello world")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult


class WriteFileTool(Tool):
    """Tool for writing content to files.

    This tool writes content to a file in the filesystem.
    It supports creating new files and overwriting existing ones.

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
    Write to a file:

        tool = WriteFileTool()
        result = await tool.execute(
            context,
            path="output.txt",
            content="Hello world"
        )

    Write with create_parents:

        result = await tool.execute(
            context,
            path="subdir/output.txt",
            content="Content",
            create_parents=True
        )
    """

    name: str = "write_file"
    description: str = "Write content to a file"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
            "create_parents": {
                "type": "boolean",
                "description": "Create parent directories if they don't exist",
                "default": False,
            },
        },
        "required": ["path", "content"],
    }

    async def execute(  # type: ignore[override]
        self,
        context: ToolContext,
        path: str,
        content: str,
        create_parents: bool = False,
    ) -> ToolResult:
        """Write content to a file.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        path : str
            Path to the file to write.
        content : str
            Content to write to the file.
        create_parents : bool, optional
            Create parent directories if they don't exist.

        Returns
        -------
        ToolResult
            The result indicating success or failure.
        """
        try:
            file_path = self._resolve_path(context, path)

            if file_path.exists() and file_path.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is a directory: {path}",
                )

            if create_parents:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                parent_dir = file_path.parent
                if not parent_dir.exists():
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Parent directory does not exist: {parent_dir}",
                    )

            file_path.write_text(content, encoding="utf-8")

            return ToolResult(
                success=True,
                output={"path": str(file_path), "bytes": len(content.encode("utf-8"))},
                metadata={"path": str(file_path)},
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
                error="Error writing file",
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
