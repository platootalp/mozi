"""Tests for mozi.capabilities.config.loader module.

This module contains unit tests for the ConfigLoader class which handles
loading configuration from multiple sources with proper priority handling.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from mozi.capabilities.config.loader import (
    ConfigLoader,
    load_config,
)
from mozi.capabilities.config.schemas import (
    AgentRegistry,
    LogLevel,
    MoziConfig,
    StorageTier,
    ToolsConfig,
)
from mozi.core.error import MoziConfigError


class TestConfigLoaderInit:
    """Tests for ConfigLoader initialization."""

    def test_default_project_dir(self) -> None:
        """Test that default project dir is .mozi in cwd."""
        loader = ConfigLoader()
        assert loader.project_config_dir == Path.cwd() / ".mozi"

    def test_default_user_config_path(self) -> None:
        """Test that default user config path is ~/.mozi/user.json."""
        loader = ConfigLoader()
        expected = Path.home() / ".mozi" / "user.json"
        assert loader.user_config_path == expected

    def test_custom_project_dir(self) -> None:
        """Test setting custom project config directory."""
        custom_path = Path("/custom/project/.mozi")
        loader = ConfigLoader(project_config_dir=custom_path)
        assert loader.project_config_dir == custom_path

    def test_custom_user_config_path(self) -> None:
        """Test setting custom user config path."""
        custom_path = Path("/custom/user.json")
        loader = ConfigLoader(user_config_path=custom_path)
        assert loader.user_config_path == custom_path


class TestConfigLoaderEnvOverrides:
    """Tests for environment variable override handling."""

    def test_env_prefix_filter(self) -> None:
        """Test that only MOZI_ prefixed vars are loaded."""
        loader = ConfigLoader()

        # Set environment variables
        os.environ["MOZI_LOGGING__LEVEL"] = "DEBUG"
        os.environ["OTHER_VAR"] = "should be ignored"

        try:
            overrides = loader._load_env_overrides()
            assert "logging.level" in overrides
            assert overrides["logging.level"] == "DEBUG"
            assert "other_var" not in overrides
        finally:
            del os.environ["MOZI_LOGGING__LEVEL"]
            del os.environ["OTHER_VAR"]

    def test_env_boolean_parsing(self) -> None:
        """Test that boolean strings are parsed correctly."""
        loader = ConfigLoader()

        os.environ["MOZI_SECURITY__HITL_ENABLED"] = "true"
        os.environ["MOZI_SECURITY__ALLOW_SECRET_ACCESS"] = "false"

        try:
            overrides = loader._load_env_overrides()
            assert overrides["security.hitl_enabled"] is True
            assert overrides["security.allow_secret_access"] is False
        finally:
            del os.environ["MOZI_SECURITY__HITL_ENABLED"]
            del os.environ["MOZI_SECURITY__ALLOW_SECRET_ACCESS"]

    def test_env_integer_parsing(self) -> None:
        """Test that integer strings are parsed correctly."""
        loader = ConfigLoader()

        os.environ["MOZI_SECURITY__HITL_TIMEOUT_SECONDS"] = "600"

        try:
            overrides = loader._load_env_overrides()
            assert overrides["security.hitl_timeout_seconds"] == 600
            assert isinstance(
                overrides["security.hitl_timeout_seconds"],
                int,
            )
        finally:
            del os.environ["MOZI_SECURITY__HITL_TIMEOUT_SECONDS"]

    def test_env_float_parsing(self) -> None:
        """Test that float strings are parsed correctly."""
        loader = ConfigLoader()

        os.environ["MOZI_TEST_VALUE"] = "3.14"

        try:
            overrides = loader._load_env_overrides()
            assert overrides["test_value"] == 3.14
            assert isinstance(overrides["test_value"], float)
        finally:
            del os.environ["MOZI_TEST_VALUE"]


class TestConfigLoaderJsonLoading:
    """Tests for JSON file loading."""

    def test_load_valid_json_file(self) -> None:
        """Test loading a valid JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump({"logging": {"level": "DEBUG"}}, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader()
            data = loader._load_json_file(temp_path)
            assert data["logging"]["level"] == "DEBUG"
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file_raises(self) -> None:
        """Test that loading non-existent file raises error."""
        loader = ConfigLoader()
        nonexistent = Path("/nonexistent/path/config.json")

        with pytest.raises(MoziConfigError, match="Configuration file not found"):
            loader._load_json_file(nonexistent)

    def test_load_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader()
            with pytest.raises(MoziConfigError, match="Invalid JSON"):
                loader._load_json_file(temp_path)
        finally:
            temp_path.unlink()

    def test_load_non_object_json_raises(self) -> None:
        """Test that non-object JSON raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(["not", "an", "object"], f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader()
            with pytest.raises(
                MoziConfigError,
                match="must contain a JSON object",
            ):
                loader._load_json_file(temp_path)
        finally:
            temp_path.unlink()


class TestConfigLoaderMerge:
    """Tests for configuration merging."""

    def test_merge_basic(self) -> None:
        """Test basic dictionary merge."""
        loader = ConfigLoader()
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = loader._merge_configs(base, override)

        assert result["a"] == 1
        assert result["b"] == 3
        assert result["c"] == 4

    def test_merge_nested(self) -> None:
        """Test nested dictionary merge."""
        loader = ConfigLoader()
        base = {"storage": {"hot": {"path": "/data/hot"}, "warm": {"path": "/data/warm"}}}
        override = {"storage": {"hot": {"path": "/new/hot"}}}
        result = loader._merge_configs(base, override)

        assert result["storage"]["hot"]["path"] == "/new/hot"
        assert result["storage"]["warm"]["path"] == "/data/warm"


class TestConfigLoaderFlatten:
    """Tests for dictionary flattening."""

    def test_flatten_simple(self) -> None:
        """Test flattening a simple nested dict."""
        loader = ConfigLoader()
        data = {"a": 1, "b": {"c": 2, "d": 3}}
        result = loader._flatten_dict(data)

        assert result["a"] == 1
        assert result["b.c"] == 2
        assert result["b.d"] == 3

    def test_flatten_deep_nesting(self) -> None:
        """Test flattening deeply nested dict."""
        loader = ConfigLoader()
        data = {"a": {"b": {"c": {"d": 1}}}}
        result = loader._flatten_dict(data)

        assert result["a.b.c.d"] == 1


class TestConfigLoaderSetNestedValue:
    """Tests for setting nested values."""

    def test_set_simple_value(self) -> None:
        """Test setting a simple value."""
        loader = ConfigLoader()
        data: dict[str, object] = {}
        loader._set_nested_value(data, "key", "value")

        assert data["key"] == "value"

    def test_set_nested_value(self) -> None:
        """Test setting a nested value."""
        loader = ConfigLoader()
        data: dict[str, object] = {}
        loader._set_nested_value(data, "storage.hot.path", "/data/hot")

        assert data["storage"]["hot"]["path"] == "/data/hot"

    def test_set_deep_nested_value(self) -> None:
        """Test setting a deeply nested value."""
        loader = ConfigLoader()
        data: dict[str, object] = {}
        loader._set_nested_value(data, "a.b.c.d", 42)

        assert data["a"]["b"]["c"]["d"] == 42


class TestConfigLoaderGet:
    """Tests for getting configuration values."""

    @pytest.fixture
    def loaded_loader(self) -> ConfigLoader:
        """Create a loader with loaded config."""
        from mozi.capabilities.config.schemas import (
            LoggingConfig,
            StorageConfig,
        )

        loader = ConfigLoader()
        loader._config = MoziConfig(
            logging=LoggingConfig(level=LogLevel.DEBUG),
            storage=StorageConfig(default_tier=StorageTier.WARM),
        )
        return loader

    def test_get_existing_key(self, loaded_loader: ConfigLoader) -> None:
        """Test getting an existing key."""
        value = loaded_loader.get("logging.level")
        assert value == LogLevel.DEBUG

    def test_get_nonexistent_key_with_default(self, loaded_loader: ConfigLoader) -> None:
        """Test getting non-existent key returns default."""
        value = loaded_loader.get("nonexistent.key", "default")
        assert value == "default"

    def test_get_without_loading_raises(self) -> None:
        """Test that get before load raises error."""
        loader = ConfigLoader()

        with pytest.raises(MoziConfigError, match="not loaded yet"):
            loader.get("any.key")


@pytest.mark.asyncio
class TestConfigLoaderLoad:
    """Tests for async load method."""

    async def test_load_with_defaults(self) -> None:
        """Test loading with just defaults."""
        loader = ConfigLoader()
        config = await loader.load()

        assert isinstance(config, MoziConfig)
        assert config.version == "1.0"
        assert config.logging.level == LogLevel.INFO

    async def test_load_with_user_config(self) -> None:
        """Test loading with user config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_config = Path(tmpdir) / "user.json"
            user_config.write_text(
                json.dumps({"logging": {"level": "ERROR"}}),
                encoding="utf-8",
            )

            loader = ConfigLoader(user_config_path=user_config)
            config = await loader.load()

            assert config.logging.level == LogLevel.ERROR

    async def test_load_with_project_config(self) -> None:
        """Test loading with project config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / ".mozi"
            project_dir.mkdir()
            config_file = project_dir / "config.json"
            config_file.write_text(
                json.dumps({"logging": {"level": "WARNING"}}),
                encoding="utf-8",
            )

            loader = ConfigLoader(project_config_dir=project_dir)
            config = await loader.load()

            assert config.logging.level == LogLevel.WARNING

    async def test_load_priority_env_over_project(self) -> None:
        """Test that env vars override project config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / ".mozi"
            project_dir.mkdir()
            config_file = project_dir / "config.json"
            config_file.write_text(
                json.dumps({"logging": {"level": "WARNING"}}),
                encoding="utf-8",
            )

            os.environ["MOZI_LOGGING__LEVEL"] = "ERROR"

            try:
                loader = ConfigLoader(project_config_dir=project_dir)
                config = await loader.load()

                assert config.logging.level == LogLevel.ERROR
            finally:
                del os.environ["MOZI_LOGGING__LEVEL"]

    async def test_load_invalid_config_raises(self) -> None:
        """Test that invalid config raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / ".mozi"
            project_dir.mkdir()
            config_file = project_dir / "config.json"
            # Invalid: extra field not allowed
            config_file.write_text(
                json.dumps({"invalid_field": "value"}),
                encoding="utf-8",
            )

            loader = ConfigLoader(project_config_dir=project_dir)

            with pytest.raises(MoziConfigError, match="Invalid configuration"):
                await loader.load()


@pytest.mark.asyncio
class TestConfigLoaderLoadAgents:
    """Tests for loading agent registry."""

    async def test_load_agents_default(self) -> None:
        """Test loading agents with defaults."""
        loader = ConfigLoader()
        registry = await loader.load_agents()

        assert isinstance(registry, AgentRegistry)
        assert registry.version == "1.0"
        assert registry.default_agent == "orchestrator"

    async def test_load_agents_from_file(self) -> None:
        """Test loading agents from project file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / ".mozi"
            project_dir.mkdir()
            agents_file = project_dir / "agents.json"
            agents_file.write_text(
                json.dumps({
                    "agents": {
                        "test-agent": {
                            "name": "test-agent",
                            "model": "claude-3-5-sonnet",
                        },
                    },
                }),
                encoding="utf-8",
            )

            loader = ConfigLoader(project_config_dir=project_dir)
            registry = await loader.load_agents()

            assert "test-agent" in registry.agents
            assert registry.agents["test-agent"].model == "claude-3-5-sonnet"


@pytest.mark.asyncio
class TestConfigLoaderLoadTools:
    """Tests for loading tools configuration."""

    async def test_load_tools_default(self) -> None:
        """Test loading tools with defaults."""
        loader = ConfigLoader()
        config = await loader.load_tools()

        assert isinstance(config, ToolsConfig)
        assert config.version == "1.0"
        assert config.builtin_tools_enabled is True

    async def test_load_tools_from_file(self) -> None:
        """Test loading tools from project file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / ".mozi"
            project_dir.mkdir()
            tools_file = project_dir / "tools.json"
            tools_file.write_text(
                json.dumps({
                    "blocklist": ["dangerous-tool"],
                    "builtin_tools_enabled": False,
                }),
                encoding="utf-8",
            )

            loader = ConfigLoader(project_config_dir=project_dir)
            config = await loader.load_tools()

            assert "dangerous-tool" in config.blocklist
            assert config.builtin_tools_enabled is False


class TestLoadConfigFunction:
    """Tests for the load_config convenience function."""

    @pytest.mark.asyncio
    async def test_load_config_returns_mozi_config(self) -> None:
        """Test that load_config returns MoziConfig."""
        config = await load_config()
        assert isinstance(config, MoziConfig)

    @pytest.mark.asyncio
    async def test_load_config_uses_defaults(self) -> None:
        """Test that load_config uses default values."""
        config = await load_config()
        assert config.version == "1.0"
        assert config.storage.default_tier == StorageTier.HOT


class TestConfigLoaderProperties:
    """Tests for ConfigLoader properties."""

    @pytest.mark.asyncio
    async def test_config_property_after_load(self) -> None:
        """Test config property is set after load."""
        loader = ConfigLoader()
        await loader.load()

        assert loader.config is not None
        assert isinstance(loader.config, MoziConfig)

    @pytest.mark.asyncio
    async def test_agents_config_property_after_load(self) -> None:
        """Test agents_config property is set after load."""
        loader = ConfigLoader()
        await loader.load_agents()

        assert loader.agents_config is not None
        assert isinstance(loader.agents_config, AgentRegistry)

    @pytest.mark.asyncio
    async def test_tools_config_property_after_load(self) -> None:
        """Test tools_config property is set after load."""
        loader = ConfigLoader()
        await loader.load_tools()

        assert loader.tools_config is not None
        assert isinstance(loader.tools_config, ToolsConfig)
