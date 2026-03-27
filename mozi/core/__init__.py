"""Core module for Mozi AI Coding Agent.

This module contains core components including error classes.

Examples
--------
Import error classes:

    from mozi.core import MoziError, MoziConfigError, MoziRuntimeError

Raise an error:

    raise MoziConfigError("Invalid configuration")
"""

from __future__ import annotations

from mozi.core.error import (
    MoziConfigError,
    MoziError,
    MoziRuntimeError,
    MoziSessionError,
    MoziToolError,
)

__all__ = [
    "MoziError",
    "MoziConfigError",
    "MoziRuntimeError",
    "MoziToolError",
    "MoziSessionError",
]
