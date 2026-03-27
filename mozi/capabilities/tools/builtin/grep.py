"""Grep tool for Mozi AI Coding Agent.

This module provides the GrepTool for searching file contents.

Examples
--------
Search for a pattern:

    tool = GrepTool()
    result = await tool.execute(context, pattern="def main")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult


class GrepTool(Tool):
    """Tool for searching file contents.

    This tool searches for patterns in files using regular expressions.
    It supports recursive directory searching and various match options.

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
    Search for a pattern:

        tool = GrepTool()
        result = await tool.execute(context, pattern="def main")

    Search with regex:

        result = await tool.execute(
            context,
            pattern=r"\\d{3}-\\d{4}",
            path=".",
            use_regex=True
        )

    Case-insensitive search:

        result = await tool.execute(
            context,
            pattern="TODO",
            path="src",
            ignore_case=True
        )
    """

    name: str = "grep"
    description: str = "Search for patterns in files"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "Path to search in (file or directory)",
                "default": ".",
            },
            "use_regex": {
                "type": "boolean",
                "description": "Treat pattern as regular expression",
                "default": True,
            },
            "ignore_case": {
                "type": "boolean",
                "description": "Case-insensitive search",
                "default": False,
            },
            "recursive": {
                "type": "boolean",
                "description": "Search recursively in directories",
                "default": True,
            },
            "file_pattern": {
                "type": "string",
                "description": "Only search in files matching this pattern",
                "default": None,
            },
        },
        "required": ["pattern"],
    }

    async def execute(  # type: ignore[override]
        self,
        context: ToolContext,
        pattern: str,
        path: str = ".",
        use_regex: bool = True,
        ignore_case: bool = False,
        recursive: bool = True,
        file_pattern: str | None = None,
    ) -> ToolResult:
        """Search for a pattern in files.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        pattern : str
            Pattern to search for.
        path : str, optional
            Path to search in (file or directory).
        use_regex : bool, optional
            Treat pattern as regular expression.
        ignore_case : bool, optional
            Case-insensitive search.
        recursive : bool, optional
            Search recursively in directories.
        file_pattern : str | None, optional
            Only search in files matching this pattern.

        Returns
        -------
        ToolResult
            The result containing matches or error.
        """
        try:
            search_path = self._resolve_path(context, path)

            if not search_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path not found: {path}",
                )

            flags = re.IGNORECASE if ignore_case else 0

            if use_regex:
                compiled_pattern = re.compile(pattern, flags)
            else:
                escaped = re.escape(pattern)
                compiled_pattern = re.compile(escaped, flags)

            matches: list[dict[str, Any]] = []

            if search_path.is_file():
                file_matches = await self._search_file(
                    search_path, compiled_pattern
                )
                matches.extend(file_matches)
            elif search_path.is_dir():
                matches.extend(
                    await self._search_directory(
                        search_path,
                        compiled_pattern,
                        recursive,
                        file_pattern,
                    )
                )

            return ToolResult(
                success=True,
                output={"matches": matches, "count": len(matches)},
                metadata={
                    "pattern": pattern,
                    "path": str(search_path),
                },
            )

        except re.error as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Invalid regex pattern: {e}",
            )
        except OSError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error searching: {e}",
            )

    async def _search_file(
        self,
        file_path: Path,
        pattern: re.Pattern[str],
    ) -> list[dict[str, Any]]:
        """Search for pattern in a single file.

        Parameters
        ----------
        file_path : Path
            Path to the file to search.
        pattern : re.Pattern[str]
            Compiled regex pattern.

        Returns
        -------
        list[dict[str, Any]]
            List of matches with line numbers and content.
        """
        matches: list[dict[str, Any]] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            for line_num, line in enumerate(lines):
                if pattern.search(line):
                    matches.append(
                        {
                            "path": str(file_path),
                            "line": line_num + 1,
                            "content": line,
                        }
                    )
        except (OSError, UnicodeDecodeError):
            pass

        return matches

    async def _search_directory(
        self,
        directory: Path,
        pattern: re.Pattern[str],
        recursive: bool,
        file_pattern: str | None,
    ) -> list[dict[str, Any]]:
        """Search for pattern in a directory.

        Parameters
        ----------
        directory : Path
            Directory to search in.
        pattern : re.Pattern[str]
            Compiled regex pattern.
        recursive : bool
            Search recursively.
        file_pattern : str | None
            Only search files matching this pattern.

        Returns
        -------
        list[dict[str, Any]]
            List of matches with line numbers and content.
        """
        matches: list[dict[str, Any]] = []

        try:
            if recursive:
                paths = directory.rglob("*")
            else:
                paths = directory.glob("*")

            for path in paths:
                if path.is_file():
                    if file_pattern is None or path.match(file_pattern):
                        file_matches = await self._search_file(path, pattern)
                        matches.extend(file_matches)
        except OSError:
            pass

        return matches

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
