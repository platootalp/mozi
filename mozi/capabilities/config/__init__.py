"""Configuration management for Mozi AI Coding Agent.

This package provides configuration loading, validation, and management
for the Mozi agent system. It handles loading from multiple sources
with proper priority (env vars > project config > user config > defaults).

Examples
--------
Load configuration:

    from mozi.capabilities.config import load_config

    config = load_config()
"""

from __future__ import annotations

from mozi.capabilities.config.schemas import (
    AgentConfig,
    AgentRegistry,
    ComplexityThreshold,
    LogFormat,
    LogLevel,
    LoggingConfig,
    ModelFallback,
    ModelProvider,
    MoziConfig,
    SecurityConfig,
    StorageConfig,
    StorageTier,
    StorageTierConfig,
    ToolGroup,
    ToolPermission,
    ToolPolicy,
    ToolsConfig,
    SandboxMode,
)

__all__ = [
    # config.py schemas
    "MoziConfig",
    "StorageConfig",
    "StorageTierConfig",
    "StorageTier",
    "LoggingConfig",
    "LogLevel",
    "LogFormat",
    "SecurityConfig",
    "ComplexityThreshold",
    # agents.py schemas
    "AgentConfig",
    "AgentRegistry",
    "AgentPermission",
    "ModelProvider",
    "ModelFallback",
    # tools.py schemas
    "ToolPolicy",
    "ToolGroup",
    "ToolsConfig",
    "ToolPermission",
    "SandboxMode",
]
