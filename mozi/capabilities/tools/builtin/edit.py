"""Edit file tool for Mozi AI Coding Agent.

This module provides the EditFileTool for editing existing files.

Examples
--------
Edit a file:

    tool = EditFileTool()
    result = await tool.execute(
        context,
        path="test.py",
        old_string="old content",
        new_string="new content"
    )
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult


class EditFileTool(Tool):
    """Tool for editing existing files.

    This tool performs find-and-replace operations on files.
    It supports exact string matching and regex patterns.

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
    Edit with exact string:

        tool = EditFileTool()
        result = await tool.execute(
            context,
            path="test.py",
            old_string="old content",
            new_string="new content"
        )

    Edit with regex:

        result = await tool.execute(
            context,
            path="test.py",
            old_string=r"\\d+",
            new_string="NUMBER",
            use_regex=True
        )
    """

    name: str = "edit_file"
    description: str = "Edit an existing file with find-and-replace"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "String or pattern to find",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement string",
            },
            "use_regex": {
                "type": "boolean",
                "description": "Use regex matching instead of exact string",
                "default": False,
            },
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def execute(  # type: ignore[override]
        self,
        context: ToolContext,
        path: str,
        old_string: str,
        new_string: str,
        use_regex: bool = False,
    ) -> ToolResult:
        """Edit a file with find-and-replace.

        Parameters
        ----------
        context : ToolContext
            The execution context.
        path : str
            Path to the file to edit.
        old_string : str
            String or pattern to find.
        new_string : str
            Replacement string.
        use_regex : bool, optional
            Use regex matching instead of exact string.

        Returns
        -------
        ToolResult
            The result indicating success or failure.
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

            if use_regex:
                pattern = re.compile(old_string)
                if not pattern.search(content):
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Pattern not found: {old_string}",
                    )
                new_content = pattern.sub(new_string, content)
                match_count = len(pattern.findall(content))
            else:
                if old_string not in content:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"String not found: {old_string}",
                    )
                new_content = content.replace(old_string, new_string)
                match_count = content.count(old_string)

            file_path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output={
                    "path": str(file_path),
                    "replacements": match_count,
                },
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
                error="Error editing file",
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
