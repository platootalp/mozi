"""Tool framework for Mozi AI Coding Agent.

This module defines the base classes and interfaces for the tool system:
- ToolContext: Context passed to tools during execution
- ToolResult: Result returned from tool execution
- Tool: Abstract base class for all tools

Examples
--------
Create a custom tool:

    class MyTool(Tool):
        name: str = "my_tool"
        description: str = "Does something useful"

        async def execute(self, context: ToolContext) -> ToolResult:
            return ToolResult(success=True, output="done")

Execute a registered tool:

    registry = ToolRegistry()
    result = await registry.execute("my_tool", context)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolContext:
    """Context passed to tools during execution.

    Attributes
    ----------
    working_directory : str
        The current working directory for tool execution.
    session_id : str | None
        The session ID if available, None otherwise.
    variables : dict[str, Any]
        Shared variables that tools can read/write.
    timeout : int
        Maximum execution time in seconds.

    Examples
    --------
    Create a context for tool execution:

        context = ToolContext(
            working_directory="/path/to/project",
            session_id="session-123",
            variables={"key": "value"},
            timeout=30
        )
    """

    working_directory: str = "."
    session_id: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    timeout: int = 30


@dataclass
class ToolResult:
    """Result returned from tool execution.

    Attributes
    ----------
    success : bool
        Whether the tool executed successfully.
    output : Any
        The output data from tool execution.
    error : str | None
        Error message if execution failed.
    metadata : dict[str, Any]
        Additional metadata about the execution.

    Examples
    --------
    Return a successful result:

        return ToolResult(success=True, output={"files": ["a.py", "b.py"]})

    Return an error result:

        return ToolResult(
            success=False,
            output=None,
            error="File not found: test.py"
        )
    """

    success: bool = False
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the result after initialization."""
        if self.success and self.error is not None:
            raise ValueError("Cannot have error message when success is True")


class Tool(ABC):
    """Abstract base class for all tools.

    All tools must inherit from this class and implement the execute method.

    Attributes
    ----------
    name : str
        Unique identifier for the tool.
    description : str
        Human-readable description of what the tool does.
    parameters : dict[str, Any]
        JSON schema for the tool's parameters.

    Examples
    --------
    Create a simple tool:

        class ReadFileTool(Tool):
            name: str = "read_file"
            description: str = "Read contents of a file"

            async def execute(self, context: ToolContext) -> ToolResult:
                # Implementation here
                pass
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given context and parameters.

        Parameters
        ----------
        context : ToolContext
            The execution context containing working directory,
            session info, and shared variables.
        **kwargs : Any
            Tool-specific parameters.

        Returns
        -------
        ToolResult
            The result of tool execution.

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
        """
        raise NotImplementedError
