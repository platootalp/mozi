"""Configuration loader for Mozi AI Coding Agent.

This module provides the ConfigLoader class that loads configuration from
multiple sources with proper priority handling. Configuration sources are
loaded in the following order (highest to lowest priority):

1. Environment variables (MOZI_* prefix)
2. Project-local config files (.mozi/*.json)
3. User-global config file (~/.mozi/user.json)
4. System defaults

Examples
--------
Load default configuration:

    loader = ConfigLoader()
    config = await loader.load()

Load from specific paths:

    loader = ConfigLoader(
        project_config_dir=Path("/path/to/.mozi"),
        user_config_path=Path("/path/to/user.json")
    )
    config = await loader.load()

Access individual config values:

    value = loader.get("storage.hot.path")
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mozi.capabilities.config.schemas import (
    AgentRegistry,
    MoziConfig,
    ToolsConfig,
)
from mozi.core.error import MoziConfigError


class ConfigLoader:
    """Configuration loader with multi-source priority support.

    This class handles loading configuration from multiple sources,
    merging them with proper priority handling. Environment variables
    take highest precedence, followed by project config, user config,
    and finally system defaults.

    Attributes
    ----------
    project_config_dir : Path | None
        Path to project-local config directory (.mozi/).
        Defaults to .mozi/ in current working directory.
    user_config_path : Path | None
        Path to user-global config file.
        Defaults to ~/.mozi/user.json.
    _config : MoziConfig | None
        Cached loaded configuration.

    Examples
    --------
    Basic usage:

        loader = ConfigLoader()
        config = await loader.load()

    With custom paths:

        loader = ConfigLoader(
            project_config_dir=Path("/my/project/.mozi"),
            user_config_path=Path.home() / ".config" / "mozi" / "user.json"
        )
        config = await loader.load()
    """

    ENV_PREFIX: str = "MOZI_"
    """Environment variable prefix for Mozi configuration."""

    DEFAULT_PROJECT_DIR: str = ".mozi"
    """Default project configuration directory name."""

    DEFAULT_USER_CONFIG: str = "user.json"
    """Default user configuration file name."""

    def __init__(
        self,
        project_config_dir: Path | None = None,
        user_config_path: Path | None = None,
    ) -> None:
        """Initialize ConfigLoader with optional custom paths.

        Parameters
        ----------
        project_config_dir : Path | None, optional
            Path to project-local config directory.
            If None, defaults to .mozi/ in current working directory.
        user_config_path : Path | None, optional
            Path to user-global config file.
            If None, defaults to ~/.mozi/user.json.
        """
        self._project_config_dir: Path | None = project_config_dir
        self._user_config_path: Path | None = user_config_path
        self._config: MoziConfig | None = None
        self._agents_config: AgentRegistry | None = None
        self._tools_config: ToolsConfig | None = None

    @property
    def project_config_dir(self) -> Path:
        """Get resolved project config directory path.

        Returns
        -------
        Path
            Path to the project configuration directory.
        """
        if self._project_config_dir is not None:
            return self._project_config_dir
        return Path.cwd() / self.DEFAULT_PROJECT_DIR

    @property
    def user_config_path(self) -> Path:
        """Get resolved user config file path.

        Returns
        -------
        Path
            Path to the user configuration file.
        """
        if self._user_config_path is not None:
            return self._user_config_path
        return Path.home() / ".mozi" / self.DEFAULT_USER_CONFIG

    def _load_json_file(self, file_path: Path) -> dict[str, Any]:
        """Load and parse a JSON configuration file.

        Parameters
        ----------
        file_path : Path
            Path to the JSON file to load.

        Returns
        -------
        dict[str, Any]
            Parsed JSON data as dictionary.

        Raises
        ------
        MoziConfigError
            If the file cannot be read or parsed.
        """
        try:
            if not file_path.exists():
                msg = f"Configuration file not found: {file_path}"
                raise MoziConfigError(msg)

            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            if not isinstance(data, dict):
                msg = f"Configuration file must contain a JSON object: {file_path}"
                raise MoziConfigError(msg)

            return data
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in configuration file: {file_path}"
            raise MoziConfigError(msg, cause=e) from e
        except OSError as e:
            msg = f"Failed to read configuration file: {file_path}"
            raise MoziConfigError(msg, cause=e) from e

    def _load_env_overrides(self) -> dict[str, Any]:
        """Load configuration overrides from environment variables.

        Environment variables with the MOZI_ prefix are converted to
        configuration keys. For example, MOZI_STORAGE__HOT__PATH becomes
        the nested key storage.hot.path.

        Returns
        -------
        dict[str, Any]
            Dictionary of configuration overrides from environment.
        """
        overrides: dict[str, Any] = {}

        for key, value in os.environ.items():
            if not key.startswith(self.ENV_PREFIX):
                continue

            # Remove prefix and convert to lowercase
            config_key = key[len(self.ENV_PREFIX) :].lower()

            # Handle double underscore as path separator
            # MOZI_STORAGE__HOT__PATH -> storage.hot.path
            parts = config_key.split("__")
            if len(parts) > 1:
                config_key = ".".join(parts)

            # Try to parse numeric and boolean values
            if value.lower() == "true":
                parsed_value: Any = True
            elif value.lower() == "false":
                parsed_value = False
            elif value.isdigit():
                parsed_value = int(value)
            else:
                try:
                    parsed_value = float(value)
                except ValueError:
                    parsed_value = value

            overrides[config_key] = parsed_value

        return overrides

    def _flatten_dict(
        self,
        data: dict[str, Any],
        parent_key: str = "",
        sep: str = ".",
    ) -> dict[str, Any]:
        """Flatten a nested dictionary to dot-notation keys.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary to flatten.
        parent_key : str, optional
            Parent key prefix for nested items.
        sep : str, optional
            Separator to use between key parts.

        Returns
        -------
        dict[str, Any]
            Flattened dictionary with dot-notation keys.
        """
        items: dict[str, Any] = {}
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key, sep))
            else:
                items[new_key] = v
        return items

    def _set_nested_value(
        self,
        data: dict[str, Any],
        key: str,
        value: Any,
    ) -> None:
        """Set a value in a nested dictionary using dot notation.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary to modify.
        key : str
            Dot-separated key path (e.g., "storage.hot.path").
        value : Any
            Value to set at the specified path.
        """
        parts = key.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def _merge_configs(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge two configuration dictionaries.

        The override dictionary takes precedence over the base dictionary.
        Nested dictionaries are merged recursively.

        Parameters
        ----------
        base : dict[str, Any]
            Base configuration dictionary.
        override : dict[str, Any]
            Override configuration dictionary.

        Returns
        -------
        dict[str, Any]
            Merged configuration dictionary.
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    async def load(self) -> MoziConfig:
        """Load and merge configuration from all sources.

        Configuration is loaded and merged in the following order:
        1. System defaults (MoziConfig model defaults)
        2. User config file (~/.mozi/user.json)
        3. Project config files (.mozi/*.json)
        4. Environment variables (MOZI_*)

        Returns
        -------
        MoziConfig
            Fully loaded and merged configuration object.

        Raises
        ------
        MoziConfigError
            If any configuration source is invalid.
        """
        # Start with defaults (Pydantic handles this)
        config_data: dict[str, Any] = {}

        # Load user config (second priority)
        if self.user_config_path.exists():
            user_data = self._load_json_file(self.user_config_path)
            config_data = self._merge_configs(config_data, user_data)

        # Load project config files (third priority)
        project_dir = self.project_config_dir
        if project_dir.exists() and project_dir.is_dir():
            # Load config.json
            config_file = project_dir / "config.json"
            if config_file.exists():
                project_config = self._load_json_file(config_file)
                config_data = self._merge_configs(config_data, project_config)

        # Apply environment variable overrides (highest priority)
        env_overrides = self._load_env_overrides()
        for key, value in env_overrides.items():
            self._set_nested_value(config_data, key, value)

        # Validate and create the config object
        try:
            self._config = MoziConfig.model_validate(config_data)
        except ValidationError as e:
            msg = "Invalid configuration values"
            raise MoziConfigError(msg, cause=e) from e

        return self._config

    async def load_agents(self) -> AgentRegistry:
        """Load agent registry configuration.

        Returns
        -------
        AgentRegistry
            Agent registry with all agent configurations.

        Raises
        ------
        MoziConfigError
            If the agents configuration is invalid.
        """
        agent_data: dict[str, Any] = {}

        # Load from project config directory
        project_dir = self.project_config_dir
        if project_dir.exists() and project_dir.is_dir():
            agents_file = project_dir / "agents.json"
            if agents_file.exists():
                agent_data = self._load_json_file(agents_file)

        # Apply environment overrides for agents
        env_overrides = self._load_env_overrides()
        for key, value in env_overrides.items():
            if key.startswith("agents."):
                self._set_nested_value(agent_data, key[7:], value)

        try:
            self._agents_config = AgentRegistry.model_validate(agent_data)
        except ValidationError as e:
            msg = "Invalid agent configuration"
            raise MoziConfigError(msg, cause=e) from e

        return self._agents_config

    async def load_tools(self) -> ToolsConfig:
        """Load tools configuration.

        Returns
        -------
        ToolsConfig
            Tools configuration with policies and settings.

        Raises
        ------
        MoziConfigError
            If the tools configuration is invalid.
        """
        tools_data: dict[str, Any] = {}

        # Load from project config directory
        project_dir = self.project_config_dir
        if project_dir.exists() and project_dir.is_dir():
            tools_file = project_dir / "tools.json"
            if tools_file.exists():
                tools_data = self._load_json_file(tools_file)

        # Apply environment overrides for tools
        env_overrides = self._load_env_overrides()
        for key, value in env_overrides.items():
            if key.startswith("tools."):
                self._set_nested_value(tools_data, key[6:], value)

        try:
            self._tools_config = ToolsConfig.model_validate(tools_data)
        except ValidationError as e:
            msg = "Invalid tools configuration"
            raise MoziConfigError(msg, cause=e) from e

        return self._tools_config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated key path.

        This method provides convenient access to nested configuration
        values using dot notation. For example:
        - "storage.hot.path"
        - "logging.level"
        - "security.hitl_enabled"

        Parameters
        ----------
        key : str
            Dot-separated key path to the configuration value.
        default : Any, optional
            Default value to return if the key is not found.

        Returns
        -------
        Any
            The configuration value at the specified path, or the default
            value if the key is not found.

        Examples
        --------
        Get a simple value:

            level = loader.get("logging.level")

        Get a nested value:

            hot_path = loader.get("storage.hot.path")

        Get with default:

            timeout = loader.get("security.hitl_timeout_seconds", 300)

        Raises
        ------
        MoziConfigError
            If the configuration has not been loaded yet.
        """
        if self._config is None:
            msg = "Configuration not loaded yet. Call load() first."
            raise MoziConfigError(msg)

        # Convert key to flattened dict format
        flattened = self._flatten_dict(
            self._config.model_dump(),
        )

        return flattened.get(key, default)

    @property
    def config(self) -> MoziConfig | None:
        """Get the loaded configuration object.

        Returns
        -------
        MoziConfig | None
            The loaded configuration, or None if not yet loaded.
        """
        return self._config

    @property
    def agents_config(self) -> AgentRegistry | None:
        """Get the loaded agent registry.

        Returns
        -------
        AgentRegistry | None
            The loaded agent registry, or None if not yet loaded.
        """
        return self._agents_config

    @property
    def tools_config(self) -> ToolsConfig | None:
        """Get the loaded tools configuration.

        Returns
        -------
        ToolsConfig | None
            The loaded tools configuration, or None if not yet loaded.
        """
        return self._tools_config


async def load_config() -> MoziConfig:
    """Load the default Mozi configuration.

    This is a convenience function that creates a ConfigLoader
    with default settings and loads the configuration.

    Returns
    -------
    MoziConfig
        The loaded configuration object.

    Raises
    ------
    MoziConfigError
        If configuration loading fails.
    """
    loader = ConfigLoader()
    return await loader.load()
