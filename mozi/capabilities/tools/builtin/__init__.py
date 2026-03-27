"""Built-in tools for Mozi AI Coding Agent.

This module provides the standard set of built-in tools:
- ReadFileTool: Read file contents
- WriteFileTool: Write content to files
- EditFileTool: Edit existing files
- BashTool: Execute bash commands
- GrepTool: Search file contents
- GlobTool: Find files by pattern

Examples
--------
Register all built-in tools:

    from mozi.capabilities.tools.builtin import register_all

    registry = register_all()

Use a specific tool:

    from mozi.capabilities.tools.builtin import ReadFileTool

    tool = ReadFileTool()
"""

from __future__ import annotations

from mozi.capabilities.tools.builtin.bash import BashTool
from mozi.capabilities.tools.builtin.edit import EditFileTool
from mozi.capabilities.tools.builtin.glob import GlobTool
from mozi.capabilities.tools.builtin.grep import GrepTool
from mozi.capabilities.tools.builtin.read import ReadFileTool
from mozi.capabilities.tools.builtin.write import WriteFileTool
from mozi.capabilities.tools.registry import ToolRegistry

__all__ = [
    "BashTool",
    "EditFileTool",
    "GlobTool",
    "GrepTool",
    "ReadFileTool",
    "WriteFileTool",
]


def register_all(registry: ToolRegistry | None = None) -> ToolRegistry:
    """Register all built-in tools with a registry.

    Parameters
    ----------
    registry : ToolRegistry | None, optional
        The registry to register tools with. Creates a new one if None.

    Returns
    -------
    ToolRegistry
        The registry with all built-in tools registered.

    Examples
    --------
    Use default registry:

        registry = register_all()

    Use existing registry:

        registry = ToolRegistry()
        register_all(registry)
    """
    if registry is None:
        registry = ToolRegistry()

    tools = [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        BashTool(),
        GrepTool(),
        GlobTool(),
    ]

    for tool in tools:
        registry.register(tool)

    return registry
