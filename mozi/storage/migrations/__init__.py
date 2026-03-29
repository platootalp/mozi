"""Database migrations module.

This module provides database migration functionality.
"""

from __future__ import annotations

from mozi.storage.migrations.manager import MigrationError, MigrationManager

__all__ = ["MigrationManager", "MigrationError"]
