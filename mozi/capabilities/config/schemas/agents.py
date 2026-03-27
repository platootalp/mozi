"""Agent configuration schema for Mozi AI Coding Agent.

This module defines the Pydantic schemas for the agent registry (agents.json).
It includes model settings, permissions, and per-agent configuration.

Examples
--------
Validate an agent configuration:

    agent_data = {
        "model": "claude-3-5-sonnet",
        "temperature": 0.7,
        "max_tokens": 4096
    }
    agent = AgentConfig(**agent_data)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentPermission(StrEnum):
    """Agent permission levels."""

    FULL = "full"
    READ_ONLY = "read-only"
    RESTRICTED = "restricted"


class ModelProvider(StrEnum):
    """Supported model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    VERTEX = "vertex"


class ModelFallback(BaseModel):
    """Model fallback configuration.

    Attributes
    ----------
    primary : str
        Primary model identifier.
    fallbacks : list[str]
        List of fallback model identifiers in order of preference.
    timeout_ms : int
        Timeout in milliseconds for API calls.
    max_retries : int
        Maximum number of retries on failure.
    """

    primary: str
    fallbacks: list[str] = Field(default_factory=list)
    timeout_ms: int = Field(default=5000, ge=1000)
    max_retries: int = Field(default=2, ge=0)


class AgentConfig(BaseModel):
    """Agent configuration schema.

    Attributes
    ----------
    name : str
        Unique agent name.
    model : str
        Model identifier (e.g., claude-3-5-sonnet, gpt-4).
    provider : ModelProvider
        Model provider type.
    temperature : float
        Sampling temperature (0.0 to 1.0).
    max_tokens : int
        Maximum tokens in response.
    permission : AgentPermission
        Agent permission level.
    enabled : bool
        Whether this agent is enabled.
    description : str | None
        Optional description of agent purpose.
    """

    name: str
    model: str
    provider: ModelProvider = ModelProvider.ANTHROPIC
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    permission: AgentPermission = AgentPermission.FULL
    enabled: bool = True
    description: str | None = None

    model_config = {"extra": "forbid"}


class AgentRegistry(BaseModel):
    """Agent registry containing all agent configurations.

    Attributes
    ----------
    version : str
        Registry version.
    default_agent : str
        Name of the default agent to use.
    agents : dict[str, AgentConfig]
        Dictionary mapping agent names to their configurations.
    model_fallback : ModelFallback | None
        Global model fallback configuration.
        Used when agent-specific fallback is not configured.
    """

    version: str = "1.0"
    default_agent: str = "orchestrator"
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    model_fallback: ModelFallback | None = None

    model_config = {"extra": "forbid"}

    def get_agent(self, name: str) -> AgentConfig | None:
        """Get agent configuration by name.

        Parameters
        ----------
        name : str
            Agent name to look up.

        Returns
        -------
        AgentConfig | None
            Agent configuration if found and enabled, None otherwise.
        """
        agent = self.agents.get(name)
        if agent is None:
            return None
        if not agent.enabled:
            return None
        return agent

    def list_enabled_agents(self) -> list[AgentConfig]:
        """List all enabled agents.

        Returns
        -------
        list[AgentConfig]
            List of enabled agent configurations.
        """
        return [agent for agent in self.agents.values() if agent.enabled]
