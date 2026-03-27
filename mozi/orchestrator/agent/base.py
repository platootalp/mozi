"""Base agent class for Mozi AI Coding Agent.

This module defines the AgentBase abstract class that provides
the foundation for all agent implementations.

Examples
--------
Create a custom agent:

    class MyAgent(AgentBase):
        async def think(self, state: AgentState) -> AgentThought:
            # Custom thinking logic
            pass
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from mozi.core import MoziError


class AgentError(MoziError):
    """Exception raised for agent-related errors.

    This exception is raised when there are issues with agent
    initialization, reasoning, or execution.

    Attributes
    ----------
    agent_name : str | None
        The name of the agent involved in the error, if known.
    """

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize AgentError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        agent_name : str | None, optional
            The name of the agent involved in the error.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.agent_name: str | None = agent_name


class ThoughtType(Enum):
    """Types of thoughts in the ReAct loop."""

    REASONING = "reasoning"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"
    ERROR = "error"


@dataclass
class AgentThought:
    """Represents a single thought in the ReAct loop.

    Attributes
    ----------
    thought_type : ThoughtType
        The type of thought.
    content : str
        The content of the thought.
    tool_name : str | None
        The name of the tool if this is an action thought.
    tool_input : dict[str, Any] | None
        The input parameters for the tool.
    timestamp : datetime
        When this thought was generated.
    """

    thought_type: ThoughtType
    content: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentState:
    """Represents the current state of the agent.

    Attributes
    ----------
    session_id : str
        The session ID this state belongs to.
    task : str
        The current task description.
    thoughts : list[AgentThought]
        History of thoughts in the current run.
    tool_results : list[dict[str, Any]]
        Results from tool executions.
    max_iterations : int
        Maximum number of iterations allowed.
    current_iteration : int
        Current iteration number.
    """

    session_id: str
    task: str
    thoughts: list[AgentThought] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    max_iterations: int = 10
    current_iteration: int = 0


@dataclass
class AgentConfig:
    """Configuration for an agent.

    Attributes
    ----------
    name : str
        The name of the agent.
    model : str | None
        The model to use. None uses default.
    temperature : float
        Sampling temperature for the model.
    max_tokens : int | None
        Maximum tokens to generate. None uses default.
    max_iterations : int
        Maximum ReAct loop iterations.
    """

    name: str = "agent"
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    max_iterations: int = 10


class AgentBase(ABC):
    """Abstract base class for all agents.

    This class defines the interface that all agent implementations
    must follow. It provides the foundation for the ReAct loop pattern.

    Attributes
    ----------
    config : AgentConfig
        The agent configuration.

    Examples
    --------
    Create a simple agent:

        class MyAgent(AgentBase):
            async def think(self, state: AgentState) -> AgentThought:
                return AgentThought(
                    thought_type=ThoughtType.FINAL,
                    content="Task completed!"
                )

        agent = MyAgent(AgentConfig(name="my_agent"))
        result = await agent.run(session_context, "Hello!")
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent.

        Parameters
        ----------
        config : AgentConfig
            The agent configuration.
        """
        self.config: AgentConfig = config

    @abstractmethod
    async def think(self, state: AgentState) -> AgentThought:
        """Process the current state and generate the next thought.

        This method implements the agent's reasoning logic.
        It analyzes the current state and decides what to do next.

        Parameters
        ----------
        state : AgentState
            The current agent state.

        Returns
        -------
        AgentThought
            The next thought to execute.

        Raises
        ------
        AgentError
            If there's an error during reasoning.
        """
        raise NotImplementedError

    @abstractmethod
    async def act(self, thought: AgentThought, state: AgentState) -> dict[str, Any]:
        """Execute the action from a thought.

        This method executes the action specified in the thought.
        For action thoughts, this typically involves tool execution.

        Parameters
        ----------
        thought : AgentThought
            The thought containing the action to execute.
        state : AgentState
            The current agent state.

        Returns
        -------
        dict[str, Any]
            The result of the action execution.

        Raises
        ------
        AgentError
            If there's an error during action execution.
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Get the agent name.

        Returns
        -------
        str
            The agent name from the configuration.
        """
        return self.config.name
