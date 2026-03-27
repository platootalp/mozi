"""Unit tests for the agent runtime.

These tests verify the ReAct loop implementation in the agent runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.capabilities.tools import ToolContext, ToolRegistry, ToolResult
from mozi.infrastructure.model.adapter import ChatMessage, ModelResponse
from mozi.orchestrator.agent.base import AgentConfig, AgentThought, AgentState, ThoughtType
from mozi.orchestrator.agent.runtime import AgentRuntime, AgentRuntimeResult, SingleAgentRuntime
from mozi.orchestrator.session.context import SessionContext, SessionState, ComplexityLevel


@pytest.fixture
def mock_model_adapter() -> MagicMock:
    """Create a mock model adapter."""
    adapter = MagicMock()
    adapter.chat = AsyncMock()
    return adapter


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Create a mock tool registry."""
    registry = MagicMock(spec=ToolRegistry)
    registry.list_tools = MagicMock(return_value=[])
    registry.execute = AsyncMock()
    return registry


@pytest.fixture
def session_context() -> SessionContext:
    """Create a test session context."""
    return SessionContext(
        session_id="test-session-123",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        complexity_score=30,
        complexity_level=ComplexityLevel.SIMPLE,
        state=SessionState.ACTIVE,
    )


@pytest.mark.unit
class TestAgentRuntime:
    """Tests for AgentRuntime class."""

    def test_init(self, mock_model_adapter: MagicMock, mock_tool_registry: MagicMock) -> None:
        """Test initialization of AgentRuntime."""
        runtime = AgentRuntime(mock_model_adapter, mock_tool_registry)
        assert runtime._model_adapter is mock_model_adapter
        assert runtime._tool_registry is mock_tool_registry

    def test_init_without_tool_registry(self, mock_model_adapter: MagicMock) -> None:
        """Test initialization without tool registry."""
        runtime = AgentRuntime(mock_model_adapter)
        assert runtime._model_adapter is mock_model_adapter
        assert runtime._tool_registry is None

    def test_build_system_prompt(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test building the system prompt."""
        runtime = AgentRuntime(mock_model_adapter)
        prompt = runtime._build_system_prompt(session_context)
        assert "test-session-123" in prompt
        assert "You are a helpful coding assistant" in prompt

    def test_parse_final_response(self, mock_model_adapter: MagicMock) -> None:
        """Test parsing a final response."""
        runtime = AgentRuntime(mock_model_adapter)
        content = "<final>The task is complete!</final>"
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.FINAL
        assert thought.content == "The task is complete!"

    def test_parse_action_response(self, mock_model_adapter: MagicMock) -> None:
        """Test parsing an action response."""
        runtime = AgentRuntime(mock_model_adapter)
        content = "I need to read the file.\n<action>\nread_file\n{\"path\": \"test.py\"}\n</action>"
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.ACTION
        assert thought.tool_name == "read_file"
        assert thought.tool_input == {"path": "test.py"}

    def test_parse_reasoning_response(self, mock_model_adapter: MagicMock) -> None:
        """Test parsing a reasoning response without action."""
        runtime = AgentRuntime(mock_model_adapter)
        content = "Let me think about this step by step..."
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.REASONING
        assert "step by step" in thought.content

    def test_parse_empty_response(self, mock_model_adapter: MagicMock) -> None:
        """Test parsing an empty response."""
        runtime = AgentRuntime(mock_model_adapter)
        content = ""
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.REASONING
        assert content in thought.content

    def test_parse_action_without_input(self, mock_model_adapter: MagicMock) -> None:
        """Test parsing an action without JSON input."""
        runtime = AgentRuntime(mock_model_adapter)
        content = "<action>\nbash\n</action>"
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.ACTION
        assert thought.tool_name == "bash"
        assert thought.tool_input == {}

    @pytest.mark.anyio
    async def test_execute_tool_success(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test successful tool execution."""
        runtime = AgentRuntime(mock_model_adapter, mock_tool_registry)
        session_context.update_metadata("working_directory", "/test")

        mock_tool_registry.execute.return_value = ToolResult(
            success=True,
            output={"files": ["a.py", "b.py"]},
        )

        result = await runtime._execute_tool(
            "list_files",
            {"path": "/test"},
            session_context,
        )

        assert result["success"] is True
        assert result["output"] == {"files": ["a.py", "b.py"]}
        mock_tool_registry.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_execute_tool_failure(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test failed tool execution."""
        runtime = AgentRuntime(mock_model_adapter, mock_tool_registry)

        mock_tool_registry.execute.return_value = ToolResult(
            success=False,
            output=None,
            error="Tool not found",
        )

        result = await runtime._execute_tool(
            "nonexistent",
            {},
            session_context,
        )

        assert result["success"] is False
        assert result["error"] == "Tool not found"

    @pytest.mark.anyio
    async def test_execute_tool_no_registry(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test tool execution with no registry."""
        runtime = AgentRuntime(mock_model_adapter, None)

        result = await runtime._execute_tool(
            "some_tool",
            {},
            session_context,
        )

        assert result["success"] is False
        assert "No tool registry available" in result["error"]

    @pytest.mark.anyio
    async def test_run_final_response(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test running the agent with a final response."""
        runtime = AgentRuntime(mock_model_adapter)

        mock_model_adapter.chat.return_value = ModelResponse(
            content="<final>Task completed successfully!</final>",
            model="claude-sonnet",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        result = await runtime.run(session_context, "Do something")

        assert result.success is True
        assert result.content == "Task completed successfully!"
        assert result.iterations == 1
        assert len(result.thoughts) == 1
        assert result.thoughts[0].thought_type == ThoughtType.FINAL

    @pytest.mark.anyio
    async def test_run_with_tool_action(
        self,
        mock_model_adapter: MagicMock,
        mock_tool_registry: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test running the agent with a tool action."""
        runtime = AgentRuntime(mock_model_adapter, mock_tool_registry)

        # First response: action, second response: final
        mock_model_adapter.chat.side_effect = [
            ModelResponse(
                content='<action>\nread_file\n{"path": "test.py"}\n</action>',
                model="claude-sonnet",
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            ),
            ModelResponse(
                content="<final>The file contains 100 lines.</final>",
                model="claude-sonnet",
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            ),
        ]

        mock_tool_registry.execute.return_value = ToolResult(
            success=True,
            output="100 lines of code",
        )

        result = await runtime.run(session_context, "Read the file test.py")

        assert result.success is True
        assert result.content == "The file contains 100 lines."
        assert result.iterations == 2
        assert len(result.tool_results) == 1
        assert result.tool_results[0]["success"] is True

    @pytest.mark.anyio
    async def test_run_max_iterations(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test running the agent with max iterations."""
        runtime = AgentRuntime(mock_model_adapter)
        config = AgentConfig(name="test", max_iterations=2)

        # Always return an action
        mock_model_adapter.chat.return_value = ModelResponse(
            content='<action>\nnoop\n</action>',
            model="claude-sonnet",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        result = await runtime.run(session_context, "Do something", config)

        assert result.success is False
        assert result.error is not None
        assert "Max iterations" in result.error
        assert result.iterations == 2

    @pytest.mark.anyio
    async def test_run_preserves_session_messages(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test that session messages are preserved after run."""
        runtime = AgentRuntime(mock_model_adapter)

        session_context.add_message("user", "Previous task")

        mock_model_adapter.chat.return_value = ModelResponse(
            content="<final>Done!</final>",
            model="claude-sonnet",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        await runtime.run(session_context, "New task")

        # Should have the previous message and the final response
        # Note: new task is added to model messages, not session_context.messages
        assert len(session_context.messages) == 2  # user previous, assistant final
        assert session_context.messages[0]["role"] == "user"
        assert session_context.messages[1]["role"] == "assistant"

    @pytest.mark.anyio
    async def test_run_model_error(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test handling model errors."""
        from mozi.infrastructure.model.adapter import ModelAdapterError, ModelProvider

        runtime = AgentRuntime(mock_model_adapter)

        mock_model_adapter.chat.side_effect = ModelAdapterError(
            "API error",
            provider=ModelProvider.ANTHROPIC,
        )

        with pytest.raises(Exception):  # AgentError
            await runtime.run(session_context, "Do something")


@pytest.mark.unit
class TestSingleAgentRuntime:
    """Tests for SingleAgentRuntime class."""

    def test_init(self, mock_model_adapter: MagicMock) -> None:
        """Test initialization of SingleAgentRuntime."""
        runtime = SingleAgentRuntime(mock_model_adapter, None, max_iterations=5)
        assert runtime._max_iterations == 5

    @pytest.mark.anyio
    async def test_run_with_defaults(
        self,
        mock_model_adapter: MagicMock,
        session_context: SessionContext,
    ) -> None:
        """Test running with default configuration."""
        runtime = SingleAgentRuntime(mock_model_adapter, None)

        mock_model_adapter.chat.return_value = ModelResponse(
            content="<final>Done!</final>",
            model="claude-sonnet",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        result = await runtime.run(session_context, "Hello")

        assert result.success is True
        assert len(result.thoughts) == 1


@pytest.mark.unit
class TestAgentRuntimeResult:
    """Tests for AgentRuntimeResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values of result."""
        result = AgentRuntimeResult()
        assert result.success is False
        assert result.content == ""
        assert result.thoughts == []
        assert result.tool_results == []
        assert result.iterations == 0
        assert result.error is None

    def test_successful_result(self) -> None:
        """Test creating a successful result."""
        thoughts = [
            AgentThought(
                thought_type=ThoughtType.FINAL,
                content="Done!",
            )
        ]
        result = AgentRuntimeResult(
            success=True,
            content="Done!",
            thoughts=thoughts,
            iterations=1,
        )
        assert result.success is True
        assert result.content == "Done!"
        assert len(result.thoughts) == 1
        assert result.iterations == 1


@pytest.mark.unit
class TestAgentThoughtParsing:
    """Tests for parsing various model response formats."""

    @pytest.fixture
    def runtime(self, mock_model_adapter: MagicMock) -> AgentRuntime:
        """Create runtime for parsing tests."""
        return AgentRuntime(mock_model_adapter)

    def test_parse_with_extra_whitespace(self, runtime: AgentRuntime) -> None:
        """Test parsing with extra whitespace."""
        content = "<final>   Answer   </final>"
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.FINAL
        assert thought.content == "Answer"

    def test_parse_multiline_final(self, runtime: AgentRuntime) -> None:
        """Test parsing multiline final content."""
        content = """<final>
        The answer is 42.
        This is the final answer.
        </final>"""
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.FINAL
        assert "42" in thought.content

    def test_parse_complex_json_input(self, runtime: AgentRuntime) -> None:
        """Test parsing action with complex JSON input."""
        content = """<action>
        search
        {"query": "test", "filters": {"type": "file"}, "limit": 10}
        </action>"""
        thought = runtime._parse_model_response(content)
        assert thought.thought_type == ThoughtType.ACTION
        assert thought.tool_name == "search"
        assert thought.tool_input == {"query": "test", "filters": {"type": "file"}, "limit": 10}
