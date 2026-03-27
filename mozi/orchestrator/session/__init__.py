"""Session management for Mozi AI Coding Agent.

This module provides session context and management functionality for
handling user sessions throughout the agent lifecycle.

Examples
--------
Create a new session:

    from mozi.orchestrator.session import SessionManager

    manager = SessionManager()
    session = await manager.create_session(complexity_score=35)
"""

from __future__ import annotations

from mozi.orchestrator.session.context import (
    ComplexityLevel,
    SessionContext,
    SessionState,
)
from mozi.orchestrator.session.manager import SessionManager

__all__ = [
    "ComplexityLevel",
    "SessionContext",
    "SessionManager",
    "SessionState",
]
