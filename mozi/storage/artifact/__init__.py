"""Artifact storage module.

This module provides artifact (large file) storage functionality.
"""

from __future__ import annotations

from mozi.storage.artifact.manager import Artifact, ArtifactStore

__all__ = ["ArtifactStore", "Artifact"]
