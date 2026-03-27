"""Tool registry for Mozi AI Coding Agent.

This module provides the ToolRegistry class for registering and executing tools.

Examples
--------
Register a tool:

    registry = ToolRegistry()
    registry.register(my_tool)

Execute a tool:

    result = await registry.execute("my_tool", context, param1="value")
"""

from __future__ import annotations

from typing import Any

from mozi.capabilities.tools.framework import Tool, ToolContext, ToolResult

__all__ = ["ToolRegistry"]


class ToolRegistry:
    """Registry for managing and executing tools.

    The registry provides tool registration, lookup, and execution
    capabilities. All tools must be registered before they can be used.

    Attributes
    ----------
    _tools : dict[str, Tool]
        Internal storage of registered tools by name.

    Examples
    --------
    Create a registry and register tools:

        registry = ToolRegistry()
        registry.register(ReadFileTool())
        registry.register(WriteFileTool())

    Execute a registered tool:

        result = await registry.execute("read_file", context, path="test.py")

    Get tool information:

        tool = registry.get("read_file")
        if tool:
            print(f"Tool: {tool.name} - {tool.description}")
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry.

        Parameters
        ----------
        tool : Tool
            The tool instance to register.

        Raises
        ------
        ValueError
            If a tool with the same name is already registered.
        TypeError
            If the provided object is not a Tool instance.

        Examples
        --------
        registry.register(ReadFileTool())
        """
        if not isinstance(tool, Tool):
            msg = f"Expected Tool instance, got {type(tool).__name__}"
            raise TypeError(msg)

        if tool.name in self._tools:
            msg = f"Tool already registered: {tool.name}"
            raise ValueError(msg)

        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool from the registry.

        Parameters
        ----------
        name : str
            The name of the tool to unregister.

        Returns
        -------
        bool
            True if the tool was unregistered, False if it wasn't found.

        Examples
        --------
        registry.unregister("read_file")
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """Get a registered tool by name.

        Parameters
        ----------
        name : str
            The name of the tool to retrieve.

        Returns
        -------
        Tool | None
            The tool if found, None otherwise.

        Examples
        --------
        tool = registry.get("read_file")
        """
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools.

        Returns
        -------
        list[dict[str, Any]]
            List of tool information dictionaries containing
            name, description, and parameters.

        Examples
        --------
        for tool_info in registry.list_tools():
            print(f"{tool_info['name']}: {tool_info['description']}")
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    async def execute(
        self,
        name: str,
        context: ToolContext,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute a registered tool.

        Parameters
        ----------
        name : str
            The name of the tool to execute.
        context : ToolContext
            The execution context.
        **kwargs : Any
            Tool-specific parameters passed to execute.

        Returns
        -------
        ToolResult
            The result of tool execution.

        Raises
        ------
        ValueError
            If the tool is not found.

        Examples
        --------
        result = await registry.execute(
            "read_file",
            context,
            path="test.py"
        )
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: {name}",
            )

        return await tool.execute(context, **kwargs)

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
