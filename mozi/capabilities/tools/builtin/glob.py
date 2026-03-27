"""Glob tool for Mozi AI Coding Agent.

This module provides the GlobTool for finding files by pattern.

Examples
--------
Find Python files:

    tool = GlobTool()
    result = await tool.execute(context, pattern="**/*.py")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult


class GlobTool(Tool):
    """Tool for finding files by pattern.

    This tool searches for files matching glob patterns.
    It supports recursive patterns and various glob options.

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
    Find all Python files:

        tool = GlobTool()
        result = await tool.execute(context, pattern="**/*.py")

    Find in specific directory:

        result = await tool.execute(
            context,
            pattern="*.py",
            path="src"
        )

    Recursive search:

        result = await tool.execute(
            context,
            pattern="**/*.txt",
            path="/path/to/search"
        )
    """

    name: str = "glob"
    description: str = "Find files by glob pattern"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match",
            },
            "path": {
                "type": "string",
                "description": "Base path for glob search",
                "default": ".",
            },
            "recursive": {
                "type": "boolean",
                "description": "Search recursively",
                "default": False,
            },
        },
        "required": ["pattern"],
    }

    async def execute(  # type: ignore[override]
        self,
        context: ToolContext,
        pattern: str,
        path: str = ".",
        recursive: bool = True,
    ) -> ToolResult:
        """Find files by glob pattern.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        pattern : str
            Glob pattern to match.
        path : str, optional
            Base path for glob search.
        recursive : bool, optional
            Search recursively.

        Returns
        -------
        ToolResult
            The result containing matched files or error.
        """
        try:
            search_path = self._resolve_path(context, path)

            if not search_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path not found: {path}",
                )

            if not search_path.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a directory: {path}",
                )

            if recursive:
                matched = [Path(p) for p in search_path.glob(f"**/{pattern}")]
            else:
                matched = [Path(p) for p in search_path.glob(pattern)]

            matched_paths = [str(p.relative_to(search_path)) for p in matched]

            return ToolResult(
                success=True,
                output={
                    "files": matched_paths,
                    "count": len(matched_paths),
                },
                metadata={
                    "pattern": pattern,
                    "path": str(search_path),
                },
            )

        except OSError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error finding files: {e}",
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
