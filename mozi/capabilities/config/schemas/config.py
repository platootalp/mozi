"""Core configuration schema for Mozi AI Coding Agent.

This module defines the Pydantic schemas for the main configuration file (config.json).
It includes storage tier settings, logging configuration, and security settings.

Examples
--------
Validate a configuration dict:

    config_data = {
        "storage": {...},
        "logging": {"level": "INFO"},
        "security": {...}
    }
    config = MoziConfig(**config_data)
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class LogLevel(StrEnum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogFormat(StrEnum):
    """Supported log output formats."""

    TEXT = "text"
    JSON = "json"


class StorageTier(StrEnum):
    """Storage tier types for tiered storage system."""

    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVE = "archive"


class SandboxMode(StrEnum):
    """Sandbox execution modes."""

    OFF = "off"
    NON_MAIN = "non-main"
    ALL = "all"


class StorageTierConfig(BaseModel):
    """Configuration for a single storage tier.

    Attributes
    ----------
    enabled : bool
        Whether this tier is enabled.
    path : Path | None
        Path to the storage directory for this tier.
        Required for hot, warm, and cold tiers.
    max_size_mb : int
        Maximum size in megabytes for this tier.
    ttl_days : int | None
        Time-to-live in days for data in this tier.
        None means no expiration.
    """

    enabled: bool = True
    path: Path | None = None
    max_size_mb: int = Field(default=1024, ge=1)
    ttl_days: int | None = None


class StorageConfig(BaseModel):
    """Storage tier configuration.

    Attributes
    ----------
    hot : StorageTierConfig
        Hot storage tier (LLM Context, in-memory).
    warm : StorageTierConfig
        Warm storage tier (vector DB + SQLite).
    cold : StorageTierConfig
        Cold storage tier (file system).
    archive : StorageTierConfig
        Archive storage tier (long-term retention).
    default_tier : StorageTier
        Default tier for new data.
    """

    hot: StorageTierConfig = Field(default_factory=lambda: StorageTierConfig(enabled=True))
    warm: StorageTierConfig = Field(default_factory=lambda: StorageTierConfig(enabled=True))
    cold: StorageTierConfig = Field(default_factory=lambda: StorageTierConfig(enabled=False))
    archive: StorageTierConfig = Field(default_factory=lambda: StorageTierConfig(enabled=False))
    default_tier: StorageTier = StorageTier.HOT

    model_config = {"extra": "forbid"}


class LoggingConfig(BaseModel):
    """Logging configuration.

    Attributes
    ----------
    level : LogLevel
        Minimum log level to output.
    format : LogFormat
        Log output format.
    file_path : Path | None
        Optional path to write logs to file.
    console : bool
        Whether to output logs to console.
    """

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT
    file_path: Path | None = None
    console: bool = True

    model_config = {"extra": "forbid"}


class SecurityConfig(BaseModel):
    """Security configuration.

    Attributes
    ----------
    api_key_env_var : str
        Environment variable name containing the API key.
    allow_secret_access : bool
        Whether to allow access to secrets from tools.
    hitl_enabled : bool
        Whether Human-in-the-Loop approval is enabled.
    hitl_timeout_seconds : int
        Timeout in seconds for HITL approval requests.
    """

    api_key_env_var: str = "MOZI_API_KEY"
    allow_secret_access: bool = False
    hitl_enabled: bool = True
    hitl_timeout_seconds: int = 300

    model_config = {"extra": "forbid"}


class ComplexityThreshold(BaseModel):
    """Complexity routing thresholds.

    Attributes
    ----------
    simple_max : int
        Maximum score for SIMPLE routing (inclusive).
    medium_max : int
        Maximum score for MEDIUM routing (inclusive).
    min_granularity : int
        Minimum score granularity for threshold adjustments.
    """

    simple_max: int = Field(default=40, ge=0, le=100)
    medium_max: int = Field(default=70, ge=0, le=100)
    min_granularity: int = Field(default=5, ge=1)


class MoziConfig(BaseModel):
    """Core Mozi configuration schema.

    This is the root configuration schema that encompasses all
    system settings including storage, logging, security, and
    complexity routing thresholds.

    Attributes
    ----------
    version : str
        Configuration file version.
    storage : StorageConfig
        Storage tier configuration.
    logging : LoggingConfig
        Logging configuration.
    security : SecurityConfig
        Security configuration.
    complexity_threshold : ComplexityThreshold
        Complexity routing thresholds.
    project_config_dir : Path | None
        Path to project-specific config directory (.mozi/).
        If None, defaults to .mozi/ in the current directory.
    user_config_path : Path | None
        Path to user global config file (~/.mozi/user.json).
        If None, defaults to ~/.mozi/user.json.
    """

    version: str = "1.0"
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    complexity_threshold: ComplexityThreshold = Field(default_factory=ComplexityThreshold)
    project_config_dir: Path | None = None
    user_config_path: Path | None = None

    model_config = {"extra": "forbid"}

    def validate_thresholds(self) -> bool:
        """Validate that thresholds are logically consistent.

        Returns
        -------
        bool
            True if simple_max < medium_max.

        Raises
        ------
        ValueError
            If simple_max >= medium_max.
        """
        if self.complexity_threshold.simple_max >= self.complexity_threshold.medium_max:
            msg = "simple_max must be less than medium_max"
            raise ValueError(msg)
        return True
