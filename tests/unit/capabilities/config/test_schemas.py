"""Tests for mozi.capabilities.config.schemas module.

This module contains unit tests for all Pydantic configuration schemas.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from mozi.capabilities.config.schemas.agents import (
    AgentConfig,
    AgentPermission,
    AgentRegistry,
    ModelFallback,
    ModelProvider,
)
from mozi.capabilities.config.schemas.config import (
    ComplexityThreshold,
    LogFormat,
    LogLevel,
    LoggingConfig,
    MoziConfig,
    SecurityConfig,
    StorageConfig,
    StorageTier,
    StorageTierConfig,
)
from mozi.capabilities.config.schemas.tools import (
    SandboxMode,
    ToolGroup,
    ToolPermission,
    ToolPolicy,
    ToolsConfig,
)


class TestStorageTierConfig:
    """Tests for StorageTierConfig schema."""

    def test_default_values(self) -> None:
        """Test default values for StorageTierConfig."""
        config = StorageTierConfig()
        assert config.enabled is True
        assert config.path is None
        assert config.max_size_mb == 1024
        assert config.ttl_days is None

    def test_custom_values(self) -> None:
        """Test custom values for StorageTierConfig."""
        config = StorageTierConfig(
            enabled=True,
            path=Path("/data/hot"),
            max_size_mb=2048,
            ttl_days=30,
        )
        assert config.enabled is True
        assert config.path == Path("/data/hot")
        assert config.max_size_mb == 2048
        assert config.ttl_days == 30

    def test_invalid_max_size(self) -> None:
        """Test that max_size_mb must be positive."""
        with pytest.raises(ValidationError):
            StorageTierConfig(max_size_mb=0)


class TestStorageConfig:
    """Tests for StorageConfig schema."""

    def test_default_tier(self) -> None:
        """Test default storage tier is HOT."""
        config = StorageConfig()
        assert config.default_tier == StorageTier.HOT

    def test_custom_tiers(self) -> None:
        """Test custom tier configuration."""
        config = StorageConfig(
            hot=StorageTierConfig(enabled=True, path=Path("/data/hot")),
            warm=StorageTierConfig(enabled=True, path=Path("/data/warm")),
            cold=StorageTierConfig(enabled=True, path=Path("/data/cold")),
        )
        assert config.hot.path == Path("/data/hot")
        assert config.warm.path == Path("/data/warm")
        assert config.cold.path == Path("/data/cold")

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            StorageConfig(invalid_field="value")


class TestLoggingConfig:
    """Tests for LoggingConfig schema."""

    def test_default_values(self) -> None:
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.file_path is None
        assert config.console is True

    def test_json_format(self) -> None:
        """Test JSON log format."""
        config = LoggingConfig(format=LogFormat.JSON)
        assert config.format == LogFormat.JSON

    def test_custom_values(self) -> None:
        """Test custom logging configuration."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            file_path=Path("/var/log/mozi.log"),
            console=False,
        )
        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.file_path == Path("/var/log/mozi.log")
        assert config.console is False


class TestSecurityConfig:
    """Tests for SecurityConfig schema."""

    def test_default_values(self) -> None:
        """Test default security configuration."""
        config = SecurityConfig()
        assert config.api_key_env_var == "MOZI_API_KEY"
        assert config.allow_secret_access is False
        assert config.hitl_enabled is True
        assert config.hitl_timeout_seconds == 300

    def test_custom_values(self) -> None:
        """Test custom security configuration."""
        config = SecurityConfig(
            api_key_env_var="MY_API_KEY",
            allow_secret_access=True,
            hitl_enabled=False,
            hitl_timeout_seconds=600,
        )
        assert config.api_key_env_var == "MY_API_KEY"
        assert config.allow_secret_access is True
        assert config.hitl_enabled is False
        assert config.hitl_timeout_seconds == 600


class TestComplexityThreshold:
    """Tests for ComplexityThreshold schema."""

    def test_default_values(self) -> None:
        """Test default thresholds."""
        config = ComplexityThreshold()
        assert config.simple_max == 40
        assert config.medium_max == 70
        assert config.min_granularity == 5

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        config = ComplexityThreshold(simple_max=30, medium_max=60)
        assert config.simple_max == 30
        assert config.medium_max == 60

    def test_threshold_validation(self) -> None:
        """Test that simple_max must be less than medium_max."""
        config = MoziConfig()
        assert config.validate_thresholds() is True

    def test_invalid_threshold_range(self) -> None:
        """Test threshold value range validation."""
        with pytest.raises(ValidationError):
            ComplexityThreshold(simple_max=-10)

        with pytest.raises(ValidationError):
            ComplexityThreshold(medium_max=150)

    def test_validate_thresholds_raises_on_invalid(self) -> None:
        """Test that validate_thresholds raises ValueError when simple_max >= medium_max."""
        config = MoziConfig(
            complexity_threshold=ComplexityThreshold(simple_max=50, medium_max=40)
        )
        with pytest.raises(ValueError, match="simple_max must be less than medium_max"):
            config.validate_thresholds()


class TestMoziConfig:
    """Tests for MoziConfig schema."""

    def test_default_values(self) -> None:
        """Test default MoziConfig."""
        config = MoziConfig()
        assert config.version == "1.0"
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.complexity_threshold, ComplexityThreshold)

    def test_custom_configuration(self) -> None:
        """Test custom MoziConfig."""
        config = MoziConfig(
            storage=StorageConfig(default_tier=StorageTier.WARM),
            logging=LoggingConfig(level=LogLevel.DEBUG),
            security=SecurityConfig(allow_secret_access=True),
        )
        assert config.storage.default_tier == StorageTier.WARM
        assert config.logging.level == LogLevel.DEBUG
        assert config.security.allow_secret_access is True

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            MoziConfig(invalid_field="value")


class TestAgentConfig:
    """Tests for AgentConfig schema."""

    def test_required_fields(self) -> None:
        """Test required fields for AgentConfig."""
        agent = AgentConfig(name="test-agent", model="claude-3-5-sonnet")
        assert agent.name == "test-agent"
        assert agent.model == "claude-3-5-sonnet"

    def test_default_values(self) -> None:
        """Test default values for AgentConfig."""
        agent = AgentConfig(name="test-agent", model="claude-3-5-sonnet")
        assert agent.provider == ModelProvider.ANTHROPIC
        assert agent.temperature == 0.7
        assert agent.max_tokens == 4096
        assert agent.permission == AgentPermission.FULL
        assert agent.enabled is True
        assert agent.description is None

    def test_custom_values(self) -> None:
        """Test custom values for AgentConfig."""
        agent = AgentConfig(
            name="custom-agent",
            model="gpt-4",
            provider=ModelProvider.OPENAI,
            temperature=0.5,
            max_tokens=8192,
            permission=AgentPermission.READ_ONLY,
            enabled=False,
            description="A custom agent",
        )
        assert agent.name == "custom-agent"
        assert agent.model == "gpt-4"
        assert agent.provider == ModelProvider.OPENAI
        assert agent.temperature == 0.5
        assert agent.max_tokens == 8192
        assert agent.permission == AgentPermission.READ_ONLY
        assert agent.enabled is False
        assert agent.description == "A custom agent"

    def test_temperature_range(self) -> None:
        """Test temperature validation."""
        AgentConfig(name="test", model="claude", temperature=0.0)
        AgentConfig(name="test", model="claude", temperature=2.0)
        with pytest.raises(ValidationError):
            AgentConfig(name="test", model="claude", temperature=-0.1)
        with pytest.raises(ValidationError):
            AgentConfig(name="test", model="claude", temperature=2.1)


class TestModelFallback:
    """Tests for ModelFallback schema."""

    def test_required_primary(self) -> None:
        """Test that primary model is required."""
        fallback = ModelFallback(primary="claude-3-5-sonnet")
        assert fallback.primary == "claude-3-5-sonnet"
        assert fallback.fallbacks == []
        assert fallback.timeout_ms == 5000
        assert fallback.max_retries == 2

    def test_custom_fallback(self) -> None:
        """Test custom fallback configuration."""
        fallback = ModelFallback(
            primary="claude-3-5-sonnet",
            fallbacks=["claude-3-haiku", "gpt-4"],
            timeout_ms=10000,
            max_retries=3,
        )
        assert fallback.primary == "claude-3-5-sonnet"
        assert fallback.fallbacks == ["claude-3-haiku", "gpt-4"]
        assert fallback.timeout_ms == 10000
        assert fallback.max_retries == 3


class TestAgentRegistry:
    """Tests for AgentRegistry schema."""

    def test_default_values(self) -> None:
        """Test default AgentRegistry."""
        registry = AgentRegistry()
        assert registry.version == "1.0"
        assert registry.default_agent == "orchestrator"
        assert registry.agents == {}
        assert registry.model_fallback is None

    def test_with_agents(self) -> None:
        """Test AgentRegistry with agents."""
        agent1 = AgentConfig(name="agent1", model="claude")
        agent2 = AgentConfig(name="agent2", model="gpt-4")
        registry = AgentRegistry(
            agents={"agent1": agent1, "agent2": agent2}
        )
        assert len(registry.agents) == 2

    def test_get_agent_found(self) -> None:
        """Test getting an existing enabled agent."""
        agent = AgentConfig(name="test-agent", model="claude", enabled=True)
        registry = AgentRegistry(agents={"test-agent": agent})
        found = registry.get_agent("test-agent")
        assert found is not None
        assert found.name == "test-agent"

    def test_get_agent_not_found(self) -> None:
        """Test getting a non-existent agent."""
        registry = AgentRegistry()
        found = registry.get_agent("nonexistent")
        assert found is None

    def test_get_agent_disabled(self) -> None:
        """Test that disabled agents are not returned."""
        agent = AgentConfig(name="test-agent", model="claude", enabled=False)
        registry = AgentRegistry(agents={"test-agent": agent})
        found = registry.get_agent("test-agent")
        assert found is None

    def test_list_enabled_agents(self) -> None:
        """Test listing only enabled agents."""
        agent1 = AgentConfig(name="enabled-agent", model="claude", enabled=True)
        agent2 = AgentConfig(name="disabled-agent", model="claude", enabled=False)
        registry = AgentRegistry(
            agents={"enabled-agent": agent1, "disabled-agent": agent2}
        )
        enabled = registry.list_enabled_agents()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled-agent"


class TestToolPolicy:
    """Tests for ToolPolicy schema."""

    def test_required_fields(self) -> None:
        """Test required fields for ToolPolicy."""
        policy = ToolPolicy(name="bash")
        assert policy.name == "bash"
        assert policy.permission == ToolPermission.ASK
        assert policy.sandbox_mode == SandboxMode.NON_MAIN

    def test_custom_values(self) -> None:
        """Test custom values for ToolPolicy."""
        policy = ToolPolicy(
            name="custom-tool",
            permission=ToolPermission.ALLOW,
            sandbox_mode=SandboxMode.ALL,
            description="A custom tool",
        )
        assert policy.name == "custom-tool"
        assert policy.permission == ToolPermission.ALLOW
        assert policy.sandbox_mode == SandboxMode.ALL
        assert policy.description == "A custom tool"


class TestToolGroup:
    """Tests for ToolGroup schema."""

    def test_required_fields(self) -> None:
        """Test required fields for ToolGroup."""
        policy = ToolPolicy(name="read")
        group = ToolGroup(name="file-ops", tools=["read", "write"], policy=policy)
        assert group.name == "file-ops"
        assert group.tools == ["read", "write"]
        assert group.policy.permission == ToolPermission.ASK


class TestToolsConfig:
    """Tests for ToolsConfig schema."""

    def test_default_values(self) -> None:
        """Test default ToolsConfig."""
        config = ToolsConfig()
        assert config.version == "1.0"
        assert config.allowlist == []
        assert config.blocklist == []
        assert config.default_permission == ToolPermission.ASK
        assert config.default_sandbox_mode == SandboxMode.NON_MAIN
        assert config.policies == {}
        assert config.groups == {}
        assert config.builtin_tools_enabled is True
        assert config.custom_tools_enabled is True

    def test_is_tool_allowed_by_blocklist(self) -> None:
        """Test that blocklist takes precedence."""
        config = ToolsConfig(blocklist=["dangerous-tool"])
        assert config.is_tool_allowed("dangerous-tool") is False

    def test_is_tool_allowed_by_allowlist(self) -> None:
        """Test allowlist filtering."""
        config = ToolsConfig(allowlist=["read", "write"])
        assert config.is_tool_allowed("read") is True
        assert config.is_tool_allowed("bash") is False

    def test_is_tool_allowed_empty_allowlist(self) -> None:
        """Test that empty allowlist allows all non-blocklisted tools."""
        config = ToolsConfig()
        assert config.is_tool_allowed("any-tool") is True

    def test_get_tool_policy_explicit(self) -> None:
        """Test getting explicit tool policy."""
        policy = ToolPolicy(name="bash", permission=ToolPermission.ALLOW)
        config = ToolsConfig(policies={"bash": policy})
        result = config.get_tool_policy("bash")
        assert result.permission == ToolPermission.ALLOW

    def test_get_tool_policy_default(self) -> None:
        """Test getting default tool policy."""
        config = ToolsConfig(
            default_permission=ToolPermission.DENY,
            default_sandbox_mode=SandboxMode.ALL,
        )
        result = config.get_tool_policy("unknown-tool")
        assert result.permission == ToolPermission.DENY
        assert result.sandbox_mode == SandboxMode.ALL

    def test_get_tool_policy_group(self) -> None:
        """Test getting tool policy from group."""
        group_policy = ToolPolicy(name="read", permission=ToolPermission.ALLOW)
        group = ToolGroup(name="file", tools=["read", "write"], policy=group_policy)
        config = ToolsConfig(groups={"file": group})
        result = config.get_tool_policy("read")
        assert result.permission == ToolPermission.ALLOW

    def test_get_permission(self) -> None:
        """Test getting permission for a tool."""
        config = ToolsConfig(default_permission=ToolPermission.ALLOW)
        assert config.get_permission("bash") == ToolPermission.ALLOW

    def test_get_sandbox_mode(self) -> None:
        """Test getting sandbox mode for a tool."""
        config = ToolsConfig(default_sandbox_mode=SandboxMode.ALL)
        assert config.get_sandbox_mode("bash") == SandboxMode.ALL


class TestConfigValidation:
    """Integration tests for configuration validation."""

    def test_valid_full_config(self) -> None:
        """Test validation of a complete configuration."""
        config = MoziConfig(
            storage=StorageConfig(
                hot=StorageTierConfig(enabled=True, path=Path("/data/hot")),
                warm=StorageTierConfig(enabled=True, path=Path("/data/warm")),
            ),
            logging=LoggingConfig(level=LogLevel.INFO),
            security=SecurityConfig(allow_secret_access=False),
            complexity_threshold=ComplexityThreshold(),
        )
        assert config.validate_thresholds() is True

    def test_invalid_config_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            MoziConfig.model_validate({"invalid": "field"})

    def test_nested_config_validation(self) -> None:
        """Test validation of nested configurations."""
        agent = AgentConfig(name="test", model="claude", temperature=0.5)
        registry = AgentRegistry(agents={"test": agent})
        assert registry.get_agent("test") is not None
        assert registry.get_agent("test").temperature == 0.5
