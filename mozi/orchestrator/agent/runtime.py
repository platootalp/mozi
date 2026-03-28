"""Agent runtime with ReAct loop implementation.

This module provides the AgentRuntime class that implements the
ReAct (Reasoning + Acting) loop for autonomous task execution.

The ReAct loop:
1. THINK: Agent reasons about current state and generates a thought
2. ACT: Agent executes an action (tool call or final response)
3. OBSERVE: Result is added to state and loop continues if needed

Examples
--------
Run an agent with the ReAct loop:

    runtime = AgentRuntime(model_adapter, tool_registry)
    result = await runtime.run(session_context, task="List files in /tmp")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from mozi.capabilities.tools import ToolContext, ToolRegistry, ToolResult
from mozi.infrastructure.model.adapter import (
    ChatMessage,
    ModelAdapter,
    ModelResponse,
)
from mozi.orchestrator.agent.base import (
    AgentConfig,
    AgentError,
    AgentState,
    AgentThought,
    ThoughtType,
)
from mozi.orchestrator.session.context import SessionContext

ACTION_PATTERN = re.compile(
    r"<action>\s*(\w+)\s*(\{[\s\S]*?\})?\s*</action>",
    re.DOTALL,
)
FINAL_PATTERN = re.compile(r"<final>\s*(.+?)\s*</final>", re.DOTALL)


@dataclass
class AgentRuntimeResult:
    """Result from an agent runtime execution.

    Attributes
    ----------
    success : bool
        Whether the execution was successful.
    content : str
        The final content/response from the agent.
    thoughts : list[AgentThought]
        All thoughts generated during execution.
    tool_results : list[dict[str, Any]]
        All tool execution results.
    iterations : int
        Number of iterations executed.
    error : str | None
        Error message if execution failed.
    """

    success: bool = False
    content: str = ""
    thoughts: list[AgentThought] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    error: str | None = None


class AgentRuntime:
    """Runtime for executing agents with the ReAct loop.

    This class manages the execution of an agent using the ReAct loop,
    which interleaves reasoning and acting to complete tasks.

    Attributes
    ----------
    model_adapter : ModelAdapter
        The model adapter for LLM interactions.
    tool_registry : ToolRegistry
        The registry for tool execution.

    Examples
    --------
    Create and run the agent runtime:

        runtime = AgentRuntime(model_adapter, tool_registry)
        result = await runtime.run(session_context, "Hello!")
    """

    SYSTEM_PROMPT = """You are a helpful coding assistant that uses tools to complete tasks.

You operate in a ReAct loop (Reasoning + Acting):
1. Think about what you need to do
2. If needed, use a tool to gather information or perform an action
3. Repeat until you can provide a final answer

When you need to use a tool, respond with:
<action>
tool_name
{{"param1": "value1", "param2": "value2"}}
</action>

When you have the final answer, respond with:
<final>
Your final answer here
</final>

Available tools: {tool_names}

Current session info:
- Session ID: {session_id}
- Working directory: {working_directory}

Remember: Be thorough but concise. Provide just the necessary information in your responses.
"""

    def __init__(
        self,
        model_adapter: ModelAdapter,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        """Initialize the agent runtime.

        Parameters
        ----------
        model_adapter : ModelAdapter
            The model adapter for LLM interactions.
        tool_registry : ToolRegistry | None, optional
            The registry for tool execution. Can be None if no tools available.
        """
        self._model_adapter: ModelAdapter = model_adapter
        self._tool_registry: ToolRegistry | None = tool_registry

    def _build_system_prompt(self, session_context: SessionContext) -> str:
        """Build the system prompt with tool information.

        Parameters
        ----------
        session_context : SessionContext
            The session context for building the prompt.

        Returns
        -------
        str
            The formatted system prompt.
        """
        tool_names = "No tools available"
        if self._tool_registry:
            tools = self._tool_registry.list_tools()
            if tools:
                tool_names = ", ".join(tool["name"] for tool in tools)

        working_dir = session_context.metadata.get("working_directory", ".")
        return self.SYSTEM_PROMPT.format(
            tool_names=tool_names,
            session_id=session_context.session_id,
            working_directory=working_dir,
        )

    def _parse_model_response(self, content: str) -> AgentThought:
        """Parse the model response to extract thought and action.

        Parameters
        ----------
        content : str
            The raw content from the model.

        Returns
        -------
        AgentThought
            The parsed agent thought.
        """
        # Check for final answer
        final_match = FINAL_PATTERN.search(content)
        if final_match:
            return AgentThought(
                thought_type=ThoughtType.FINAL,
                content=final_match.group(1).strip(),
            )

        # Check for action
        action_match = ACTION_PATTERN.search(content)
        if action_match:
            tool_name = action_match.group(1)
            tool_input_str = action_match.group(2)
            tool_input: dict[str, Any] = {}
            if tool_input_str:
                try:
                    tool_input = json.loads(tool_input_str.strip())
                except json.JSONDecodeError:
                    tool_input = {}

            reasoning = content[: action_match.start()].strip()
            if not reasoning:
                reasoning = f"Taking action: {tool_name}"

            return AgentThought(
                thought_type=ThoughtType.ACTION,
                content=reasoning,
                tool_name=tool_name,
                tool_input=tool_input,
            )

        # No recognized pattern, treat as reasoning
        return AgentThought(
            thought_type=ThoughtType.REASONING,
            content=content,
        )

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        session_context: SessionContext,
    ) -> dict[str, Any]:
        """Execute a tool and return the result.

        Parameters
        ----------
        tool_name : str
            The name of the tool to execute.
        tool_input : dict[str, Any]
            The input parameters for the tool.
        session_context : SessionContext
            The session context.

        Returns
        -------
        dict[str, Any]
            The tool execution result.
        """
        if self._tool_registry is None:
            return {
                "success": False,
                "output": None,
                "error": "No tool registry available",
            }

        working_dir = session_context.metadata.get("working_directory", ".")
        tool_context = ToolContext(
            working_directory=working_dir,
            session_id=session_context.session_id,
            variables=session_context.metadata.get("variables", {}),
        )

        result: ToolResult = await self._tool_registry.execute(
            tool_name,
            tool_context,
            **tool_input,
        )

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata,
        }

    def _build_messages(
        self,
        session_context: SessionContext,
        state: AgentState,
    ) -> list[ChatMessage]:
        """Build the message list for the model.

        Parameters
        ----------
        session_context : SessionContext
            The session context.
        state : AgentState
            The current agent state.

        Returns
        -------
        list[ChatMessage]
            The list of messages for the model.
        """
        messages: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=self._build_system_prompt(session_context),
            ),
        ]

        # Add conversation history from session
        for msg in session_context.messages:
            messages.append(
                ChatMessage(
                    role=msg["role"],
                    content=msg["content"],
                )
            )

        # Add task as user message if this is a new task
        if state.current_iteration == 1:
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"Task: {state.task}",
                )
            )

        # Add previous tool results as observations
        for tool_result in state.tool_results:
            obs_content = f"Observation: {json.dumps(tool_result, indent=2)}"
            messages.append(
                ChatMessage(
                    role="user",
                    content=obs_content,
                )
            )

        return messages

    async def run(
        self,
        session_context: SessionContext,
        task: str,
        agent_config: AgentConfig | None = None,
    ) -> AgentRuntimeResult:
        """Run the ReAct loop to complete a task.

        Parameters
        ----------
        session_context : SessionContext
            The session context for this execution.
        task : str
            The task description to execute.
        agent_config : AgentConfig | None, optional
            Additional agent configuration. Uses defaults if not provided.

        Returns
        -------
        AgentRuntimeResult
            The result of the execution.

        Raises
        ------
        AgentError
            If there's an error during execution.
        """
        config = agent_config or AgentConfig(name="default")
        state = AgentState(
            session_id=session_context.session_id,
            task=task,
            max_iterations=config.max_iterations,
        )

        try:
            while state.current_iteration < state.max_iterations:
                state.current_iteration += 1

                # Build messages and get model response
                messages = self._build_messages(session_context, state)
                response: ModelResponse = await self._model_adapter.chat(
                    messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )

                # Parse the model's response
                thought = self._parse_model_response(response.content)
                thought.timestamp = session_context.metadata.get(
                    "_now", lambda: __import__("datetime").datetime.now()
                )()
                state.thoughts.append(thought)

                # Handle thought based on type
                if thought.thought_type == ThoughtType.FINAL:
                    session_context.add_message("assistant", thought.content)
                    return AgentRuntimeResult(
                        success=True,
                        content=thought.content,
                        thoughts=state.thoughts,
                        tool_results=state.tool_results,
                        iterations=state.current_iteration,
                    )

                elif thought.thought_type == ThoughtType.ACTION:
                    if thought.tool_name is None:
                        state.thoughts.append(
                            AgentThought(
                                thought_type=ThoughtType.ERROR,
                                content="No tool name specified in action",
                            )
                        )
                        continue

                    # Execute the tool
                    tool_result = await self._execute_tool(
                        thought.tool_name,
                        thought.tool_input or {},
                        session_context,
                    )
                    state.tool_results.append(tool_result)

                    session_context.add_message(
                        "assistant",
                        f"<action>\n{thought.tool_name}\n"
                        f"{json.dumps(thought.tool_input or {}, indent=2)}"
                        f"\n</action>",
                    )

                # Add reasoning thought to messages
                if thought.thought_type == ThoughtType.REASONING:
                    session_context.add_message("assistant", thought.content)

            # Max iterations reached
            return AgentRuntimeResult(
                success=False,
                content="",
                thoughts=state.thoughts,
                tool_results=state.tool_results,
                iterations=state.current_iteration,
                error=f"Max iterations ({state.max_iterations}) reached",
            )

        except Exception as e:
            raise AgentError(
                f"Error during agent execution: {e}",
                agent_name=config.name,
                cause=e,
            ) from e


class SingleAgentRuntime(AgentRuntime):
    """Runtime for a single agent with default configuration.

    This is a convenience class that creates an agent runtime
    with sensible defaults for simple use cases.

    Examples
    --------
    Use the simplified runtime:

        runtime = SingleAgentRuntime(model_adapter)
        result = await runtime.run(session_context, "Hello!")
    """

    def __init__(
        self,
        model_adapter: ModelAdapter,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = 10,
    ) -> None:
        """Initialize the single agent runtime.

        Parameters
        ----------
        model_adapter : ModelAdapter
            The model adapter for LLM interactions.
        tool_registry : ToolRegistry | None, optional
            The registry for tool execution.
        max_iterations : int, optional
            Maximum iterations for the ReAct loop. Default is 10.
        """
        super().__init__(model_adapter, tool_registry)
        self._max_iterations: int = max_iterations

    async def run(
        self,
        session_context: SessionContext,
        task: str,
        agent_config: AgentConfig | None = None,
    ) -> AgentRuntimeResult:
        """Run the ReAct loop with default configuration.

        Parameters
        ----------
        session_context : SessionContext
            The session context for this execution.
        task : str
            The task description to execute.
        agent_config : AgentConfig | None, optional
            Additional agent configuration. Uses default if not provided.

        Returns
        -------
        AgentRuntimeResult
            The result of the execution.
        """
        config = agent_config or AgentConfig(
            name="single_agent",
            max_iterations=self._max_iterations,
        )
        return await super().run(session_context, task, config)
