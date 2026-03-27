"""Tests for the tool framework.

This module contains unit tests for the tool framework including
ToolContext, ToolResult, Tool, and ToolRegistry.

Examples
--------
Run all tests:

    pytest tests/unit/capabilities/tools/test_framework.py -v
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mozi.capabilities.tools import Tool, ToolContext, ToolRegistry, ToolResult
from mozi.capabilities.tools.builtin import (
    BashTool,
    EditFileTool,
    GlobTool,
    GrepTool,
    ReadFileTool,
    WriteFileTool,
    register_all,
)


class DummyTool(Tool):
    """A dummy tool for testing purposes."""

    name: str = "dummy"
    description: str = "A dummy tool for testing"

    async def execute(self, context: ToolContext, **kwargs: object) -> ToolResult:
        """Execute the dummy tool."""
        return ToolResult(success=True, output=kwargs)


@pytest.mark.unit
class TestToolContext:
    """Tests for ToolContext."""

    def test_default_values(self) -> None:
        """Test default values for ToolContext."""
        context = ToolContext()
        assert context.working_directory == "."
        assert context.session_id is None
        assert context.variables == {}
        assert context.timeout == 30

    def test_custom_values(self) -> None:
        """Test custom values for ToolContext."""
        context = ToolContext(
            working_directory="/test",
            session_id="session-123",
            variables={"key": "value"},
            timeout=60,
        )
        assert context.working_directory == "/test"
        assert context.session_id == "session-123"
        assert context.variables == {"key": "value"}
        assert context.timeout == 60


@pytest.mark.unit
class TestToolResult:
    """Tests for ToolResult."""

    def test_successful_result(self) -> None:
        """Test creating a successful result."""
        result = ToolResult(success=True, output={"data": "test"})
        assert result.success is True
        assert result.output == {"data": "test"}
        assert result.error is None
        assert result.metadata == {}

    def test_error_result(self) -> None:
        """Test creating an error result."""
        result = ToolResult(success=False, output=None, error="Something went wrong")
        assert result.success is False
        assert result.output is None
        assert result.error == "Something went wrong"

    def test_result_with_metadata(self) -> None:
        """Test result with metadata."""
        result = ToolResult(
            success=True,
            output="data",
            metadata={"key": "value"},
        )
        assert result.metadata == {"key": "value"}

    def test_invalid_result_with_error_and_success(self) -> None:
        """Test that success=True with error raises ValueError."""
        with pytest.raises(ValueError, match="Cannot have error message"):
            ToolResult(success=True, output="data", error="error")


@pytest.mark.unit
class TestTool:
    """Tests for the Tool base class."""

    def test_tool_attributes(self) -> None:
        """Test that tools have required attributes."""
        tool = DummyTool()
        assert tool.name == "dummy"
        assert tool.description == "A dummy tool for testing"

    @pytest.mark.asyncio
    async def test_tool_abstract_execute(self) -> None:
        """Test that Tool.execute is abstract."""
        tool = DummyTool()
        context = ToolContext()
        result = await tool.execute(context, key="value")
        assert result.success is True
        assert result.output == {"key": "value"}


@pytest.mark.unit
class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_empty_registry(self) -> None:
        """Test creating an empty registry."""
        registry = ToolRegistry()
        assert len(registry) == 0
        assert "dummy" not in registry

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert len(registry) == 1
        assert "dummy" in registry

    def test_register_duplicate_tool(self) -> None:
        """Test that registering duplicate tool raises ValueError."""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool)

    def test_register_non_tool_raises(self) -> None:
        """Test that registering non-Tool raises TypeError."""
        registry = ToolRegistry()
        with pytest.raises(TypeError, match="Expected Tool instance"):
            registry.register("not a tool")  # type: ignore

    def test_unregister_tool(self) -> None:
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert registry.unregister("dummy") is True
        assert len(registry) == 0
        assert "dummy" not in registry

    def test_unregister_nonexistent_tool(self) -> None:
        """Test that unregistering nonexistent tool returns False."""
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_get_tool(self) -> None:
        """Test getting a registered tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        retrieved = registry.get("dummy")
        assert retrieved is tool

    def test_get_nonexistent_tool(self) -> None:
        """Test getting a nonexistent tool returns None."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self) -> None:
        """Test listing all registered tools."""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        tools_list = registry.list_tools()
        assert len(tools_list) == 1
        assert tools_list[0]["name"] == "dummy"
        assert tools_list[0]["description"] == "A dummy tool for testing"

    @pytest.mark.asyncio
    async def test_execute_tool(self) -> None:
        """Test executing a registered tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        context = ToolContext()
        result = await registry.execute("dummy", context, key="value")
        assert result.success is True
        assert result.output == {"key": "value"}

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self) -> None:
        """Test executing a nonexistent tool returns error."""
        registry = ToolRegistry()
        context = ToolContext()
        result = await registry.execute("nonexistent", context)
        assert result.success is False
        assert "not found" in result.error


@pytest.mark.unit
class TestReadFileTool:
    """Tests for ReadFileTool."""

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
        ) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            return Path(f.name)

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        return Path(tempfile.mkdtemp())

    @pytest.mark.asyncio
    async def test_read_file(self, temp_file: Path) -> None:
        """Test reading a file."""
        tool = ReadFileTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(context, path=temp_file.name)
        assert result.success is True
        assert "Line 1" in result.output
        assert result.metadata["lines"] == 3

    @pytest.mark.asyncio
    async def test_read_file_with_limit(self, temp_file: Path) -> None:
        """Test reading a file with line limit."""
        tool = ReadFileTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(context, path=temp_file.name, limit=2)
        assert result.success is True
        assert result.metadata["lines"] == 2

    @pytest.mark.asyncio
    async def test_read_file_with_offset(self, temp_file: Path) -> None:
        """Test reading a file with offset."""
        tool = ReadFileTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(context, path=temp_file.name, offset=1)
        assert result.success is True
        assert "Line 2" in result.output
        assert "Line 1" not in result.output

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_dir: Path) -> None:
        """Test reading a nonexistent file."""
        tool = ReadFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, path="nonexistent.txt")
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_read_directory_error(self, temp_dir: Path) -> None:
        """Test reading a directory as file."""
        tool = ReadFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, path=".")
        assert result.success is False


@pytest.mark.unit
class TestWriteFileTool:
    """Tests for WriteFileTool."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        return Path(tempfile.mkdtemp())

    @pytest.mark.asyncio
    async def test_write_file(self, temp_dir: Path) -> None:
        """Test writing a file."""
        tool = WriteFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(
            context,
            path="test.txt",
            content="Hello World",
        )
        assert result.success is True
        output_path = Path(temp_dir) / "test.txt"
        assert output_path.exists()
        assert output_path.read_text() == "Hello World"

    @pytest.mark.asyncio
    async def test_write_file_with_parents(self, temp_dir: Path) -> None:
        """Test writing a file with create_parents=True."""
        tool = WriteFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(
            context,
            path="subdir/test.txt",
            content="Hello",
            create_parents=True,
        )
        assert result.success is True
        output_path = Path(temp_dir) / "subdir" / "test.txt"
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_write_file_without_parents_fails(self, temp_dir: Path) -> None:
        """Test writing to nested path without create_parents fails."""
        tool = WriteFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(
            context,
            path="nonexistent_dir/test.txt",
            content="Hello",
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_overwrite_file(self, temp_dir: Path) -> None:
        """Test overwriting an existing file."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Original")

        tool = WriteFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(
            context,
            path="test.txt",
            content="Overwritten",
        )
        assert result.success is True
        assert test_file.read_text() == "Overwritten"


@pytest.mark.unit
class TestEditFileTool:
    """Tests for EditFileTool."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        return Path(tempfile.mkdtemp())

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
        ) as f:
            f.write("Hello World\nLine 2\nLine 3\n")
            return Path(f.name)

    @pytest.mark.asyncio
    async def test_edit_file(self, temp_file: Path) -> None:
        """Test editing a file with exact string."""
        tool = EditFileTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(
            context,
            path=temp_file.name,
            old_string="World",
            new_string="Mozi",
        )
        assert result.success is True
        assert "Mozi" in temp_file.read_text()
        assert "World" not in temp_file.read_text()

    @pytest.mark.asyncio
    async def test_edit_file_with_regex(self, temp_file: Path) -> None:
        """Test editing a file with regex."""
        tool = EditFileTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(
            context,
            path=temp_file.name,
            old_string=r"Line \d+",
            new_string="Replaced",
            use_regex=True,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_edit_file_not_found(self, temp_dir: Path) -> None:
        """Test editing a nonexistent file."""
        tool = EditFileTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(
            context,
            path="nonexistent.txt",
            old_string="old",
            new_string="new",
        )
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_edit_string_not_found(self, temp_file: Path) -> None:
        """Test editing with string not found in file."""
        tool = EditFileTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(
            context,
            path=temp_file.name,
            old_string="NotPresent",
            new_string="new",
        )
        assert result.success is False
        assert "not found" in result.error


@pytest.mark.unit
class TestBashTool:
    """Tests for BashTool."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        return Path(tempfile.mkdtemp())

    @pytest.mark.asyncio
    async def test_bash_echo(self, temp_dir: Path) -> None:
        """Test executing a simple echo command."""
        tool = BashTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, command="echo 'Hello'")
        assert result.success is True
        assert "Hello" in result.output["stdout"]  # type: ignore

    @pytest.mark.asyncio
    async def test_bash_exit_code(self, temp_dir: Path) -> None:
        """Test that failed commands return exit code in output."""
        tool = BashTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, command="exit 1")
        assert result.success is False
        assert result.output["exit_code"] == 1  # type: ignore

    @pytest.mark.asyncio
    async def test_bash_timeout(self, temp_dir: Path) -> None:
        """Test command timeout."""
        tool = BashTool()
        context = ToolContext(working_directory=temp_dir, timeout=5)
        result = await tool.execute(context, command="sleep 10", timeout=2)
        assert result.success is False
        assert "timed out" in result.error


@pytest.mark.unit
class TestGrepTool:
    """Tests for GrepTool."""

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
        ) as f:
            f.write("def main():\n")
            f.write("    print('hello')\n")
            f.write("    return 0\n")
            return Path(f.name)

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        return Path(tempfile.mkdtemp())

    @pytest.mark.asyncio
    async def test_grep_file(self, temp_file: Path) -> None:
        """Test grepping in a file."""
        tool = GrepTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(
            context,
            pattern="def main",
            path=temp_file.name,
        )
        assert result.success is True
        assert result.output["count"] == 1  # type: ignore

    @pytest.mark.asyncio
    async def test_grep_directory(self, temp_file: Path) -> None:
        """Test grepping in a directory."""
        tool = GrepTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(
            context,
            pattern="return",
            path=".",
        )
        assert result.success is True
        assert result.output["count"] >= 1  # type: ignore

    @pytest.mark.asyncio
    async def test_grep_case_insensitive(self, temp_file: Path) -> None:
        """Test case-insensitive grep."""
        tool = GrepTool()
        context = ToolContext(working_directory=temp_file.parent)
        result = await tool.execute(
            context,
            pattern="DEF MAIN",
            path=temp_file.name,
            ignore_case=True,
        )
        assert result.success is True
        assert result.output["count"] == 1  # type: ignore

    @pytest.mark.asyncio
    async def test_grep_nonexistent_path(self, temp_dir: Path) -> None:
        """Test grepping nonexistent path."""
        tool = GrepTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(
            context,
            pattern="test",
            path="nonexistent",
        )
        assert result.success is False
        assert "not found" in result.error


@pytest.mark.unit
class TestGlobTool:
    """Tests for GlobTool."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory with test files."""
        temp = Path(tempfile.mkdtemp())
        (temp / "test1.txt").write_text("1")
        (temp / "test2.txt").write_text("2")
        (temp / "test.py").write_text("3")
        (temp / "subdir").mkdir()
        (temp / "subdir" / "test3.txt").write_text("4")
        return temp

    @pytest.mark.asyncio
    async def test_glob_files(self, temp_dir: Path) -> None:
        """Test globbing for files."""
        tool = GlobTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, pattern="*.txt", recursive=False)
        assert result.success is True
        assert result.output["count"] == 2  # type: ignore

    @pytest.mark.asyncio
    async def test_glob_recursive(self, temp_dir: Path) -> None:
        """Test recursive globbing."""
        tool = GlobTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, pattern="**/*.txt", recursive=True)
        assert result.success is True
        assert result.output["count"] == 3  # type: ignore

    @pytest.mark.asyncio
    async def test_glob_nonexistent_path(self, temp_dir: Path) -> None:
        """Test globbing nonexistent path."""
        tool = GlobTool()
        context = ToolContext(working_directory=temp_dir)
        result = await tool.execute(context, pattern="*.txt", path="nonexistent")
        assert result.success is False
        assert "not found" in result.error


@pytest.mark.unit
class TestRegisterAll:
    """Tests for register_all function."""

    def test_register_all(self) -> None:
        """Test registering all built-in tools."""
        registry = register_all()
        assert len(registry) == 6
        assert "read_file" in registry
        assert "write_file" in registry
        assert "edit_file" in registry
        assert "bash" in registry
        assert "grep" in registry
        assert "glob" in registry

    def test_register_all_creates_new_registry(self) -> None:
        """Test that register_all creates a new registry if none provided."""
        registry = register_all()
        assert isinstance(registry, ToolRegistry)

    def test_register_all_to_existing_registry(self) -> None:
        """Test registering to an existing registry."""
        registry = ToolRegistry()
        register_all(registry)
        assert len(registry) == 6
