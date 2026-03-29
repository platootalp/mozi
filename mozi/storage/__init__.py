"""Storage module for Mozi AI Coding Agent.

This module provides persistent storage for:
- Session: User session persistence
- Config: Configuration management
- Artifact: Large file storage

All operations are async and use SQLite for metadata storage.
"""

from __future__ import annotations

from mozi.storage.artifact.manager import Artifact, ArtifactStore
from mozi.storage.base import BaseStore
from mozi.storage.config.loader import ConfigStore
from mozi.storage.migrations import MigrationManager
from mozi.storage.session.manager import SessionStore
from mozi.storage.session.schema import (
    ComplexityLevel,
    Session,
    SessionStatus,
)

__all__ = [
    "BaseStore",
    "SessionStore",
    "Session",
    "SessionStatus",
    "ComplexityLevel",
    "ConfigStore",
    "ArtifactStore",
    "Artifact",
    "MigrationManager",
]

__version__: str = "0.1.0"
