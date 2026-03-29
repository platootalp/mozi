"""Configuration loader for Mozi.

This module provides configuration management with support for
environment variables, config files, and defaults.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConfigStore:
    """Configuration storage manager.

    This class manages configuration with support for multiple layers:
    1. Environment variables (highest priority)
    2. User config file
    3. Default config (lowest priority)

    Attributes
    ----------
    config_dir : Path
        Directory containing configuration files.
    config_path : Path
        Path to the main config file.

    Examples
    --------
    Load configuration:

        store = ConfigStore(Path("~/.mozi"))
        model_name = store.get("model.name")

    Set a configuration value:

        store.set("tools.timeout", 60)
        await store.save()
    """

    def __init__(self, config_dir: Path) -> None:
        """Initialize the configuration store.

        Parameters
        ----------
        config_dir : Path
            Directory containing configuration files.
        """
        self.config_dir = config_dir
        self.config_path = config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from all sources."""
        # 1. Load default config
        self._config = self._get_default_config()

        # 2. Load user config file
        if self.config_path.exists():
            with open(self.config_path) as f:
                user_config = json.load(f)
                self._config.update(user_config)

        # 3. Load environment variables (override)
        self._config.update(self._load_env_config())

    def _get_default_config(self) -> dict[str, Any]:
        """Get the default configuration.

        Returns
        -------
        dict[str, Any]
            Default configuration dictionary.
        """
        return {
            "model": {
                "provider": "anthropic",
                "name": "claude-sonnet-4-20250514",
            },
            "memory": {
                "working_max_size": 100000,
                "short_term_ttl_days": 180,
            },
            "security": {
                "sandbox_mode": "off",
                "hitl_enabled": False,
            },
            "tools": {
                "timeout": 30,
                "allowed_commands": ["git", "npm", "pip"],
            },
        }

    def _load_env_config(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Returns
        -------
        dict[str, Any]
            Configuration from environment variables.
        """
        env_config: dict[str, Any] = {}

        if model := os.getenv("MOZI_MODEL"):
            env_config.setdefault("model", {})["name"] = model

        if path := os.getenv("MOZI_CONFIG_PATH"):
            env_config["config_path"] = path

        return env_config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Parameters
        ----------
        key : str
            Dot-separated key path (e.g., "model.name").
        default : Any
            Default value if key not found.

        Returns
        -------
        Any
            The configuration value or default.
        """
        keys = key.split(".")
        value: Any = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Parameters
        ----------
        key : str
            Dot-separated key path (e.g., "tools.timeout").
        value : Any
            Value to set.
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    async def save(self) -> None:
        """Save configuration to file.

        This method writes the current configuration to the config file.
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    @property
    def config(self) -> dict[str, Any]:
        """Get the full configuration dictionary.

        Returns
        -------
        dict[str, Any]
            The complete configuration.
        """
        return self._config.copy()
