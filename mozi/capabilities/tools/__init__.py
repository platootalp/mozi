"""Tool framework for Mozi AI Coding Agent.

This module provides the tool infrastructure for the Capabilities layer,
including the base classes and the tool registry.

Examples
--------
Register and execute a tool:

    from mozi.capabilities.tools import ToolRegistry, ToolContext

    registry = ToolRegistry()
    context = ToolContext(working_directory=".")

    result = await registry.execute("bash", context, command="ls -la")
"""

from __future__ import annotations

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult
from mozi.capabilities.tools.registry import ToolRegistry

__all__ = [
    "Tool",
    "ToolContext",
    "ToolResult",
    "ToolRegistry",
]
