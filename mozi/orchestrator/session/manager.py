"""Session manager for Mozi AI Coding Agent.

This module provides the SessionManager class that handles session lifecycle
including creation, retrieval, updating, and persistence of sessions.

Examples
--------
Create a new session:

    manager = SessionManager(db)
    session = await manager.create_session(complexity_score=35)

Get an existing session:

    session = await manager.get_session("sess_abc123")

List all active sessions:

    sessions = await manager.list_sessions(state="ACTIVE")
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from mozi.core.error import MoziSessionError
from mozi.orchestrator.session.context import SessionContext


class SessionManager:
    """Manages session lifecycle.

    This class provides async methods for creating, retrieving, updating,
    and deleting sessions. It uses the database layer for persistence.

    Attributes
    ----------
    _sessions : dict[str, SessionContext]
        In-memory cache of active sessions.

    Examples
    --------
    Create and use a session manager:

        manager = SessionManager()
        session = await manager.create_session(complexity_score=50)
        await manager.save_session(session)
    """

    def __init__(self) -> None:
        """Initialize the session manager."""
        self._sessions: dict[str, SessionContext] = {}

    async def create_session(
        self,
        complexity_score: int = 0,
        complexity_level: str = "SIMPLE",
        metadata: dict[str, Any] | None = None,
    ) -> SessionContext:
        """Create a new session.

        Parameters
        ----------
        complexity_score : int, optional
            Initial complexity score (0-100). Defaults to 0.
        complexity_level : str, optional
            Initial complexity level. Defaults to "SIMPLE".
        metadata : dict[str, Any] | None, optional
            Initial metadata for the session. Defaults to None.

        Returns
        -------
        SessionContext
            The newly created session context.

        Raises
        ------
        MoziSessionError
            If session creation fails.
        """
        try:
            now = datetime.now()
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

            session = SessionContext(
                session_id=session_id,
                created_at=now,
                updated_at=now,
                complexity_score=complexity_score,
                complexity_level=complexity_level,
                state="ACTIVE",
                metadata=metadata or {},
            )

            self._sessions[session_id] = session
            return session

        except Exception as e:
            msg = "Failed to create session"
            raise MoziSessionError(msg, cause=e) from e

    async def get_session(self, session_id: str) -> SessionContext:
        """Retrieve a session by ID.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        SessionContext
            The session context.

        Raises
        ------
        MoziSessionError
            If session is not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            msg = f"Session not found: {session_id}"
            raise MoziSessionError(msg, session_id=session_id)

        return session

    async def update_session(self, session: SessionContext) -> SessionContext:
        """Update an existing session.

        Parameters
        ----------
        session : SessionContext
            The session context to update.

        Returns
        -------
        SessionContext
            The updated session context.

        Raises
        ------
        MoziSessionError
            If session update fails.
        """
        try:
            if session.session_id not in self._sessions:
                msg = f"Session not found: {session.session_id}"
                raise MoziSessionError(msg, session_id=session.session_id)

            session.updated_at = datetime.now()
            self._sessions[session.session_id] = session
            return session

        except MoziSessionError:
            raise
        except Exception as e:
            msg = "Failed to update session"
            raise MoziSessionError(msg, session_id=session.session_id, cause=e) from e

    async def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Raises
        ------
        MoziSessionError
            If session deletion fails or session not found.
        """
        try:
            if session_id not in self._sessions:
                msg = f"Session not found: {session_id}"
                raise MoziSessionError(msg, session_id=session_id)

            del self._sessions[session_id]

        except MoziSessionError:
            raise
        except Exception as e:
            msg = "Failed to delete session"
            raise MoziSessionError(msg, session_id=session_id, cause=e) from e

    async def list_sessions(
        self,
        state: str | None = None,
        complexity_level: str | None = None,
    ) -> list[SessionContext]:
        """List sessions with optional filtering.

        Parameters
        ----------
        state : str | None, optional
            Filter by session state (e.g., "ACTIVE", "COMPLETED").
        complexity_level : str | None, optional
            Filter by complexity level.

        Returns
        -------
        list[SessionContext]
            List of matching session contexts.
        """
        sessions = list(self._sessions.values())

        if state is not None:
            sessions = [s for s in sessions if s.state == state]

        if complexity_level is not None:
            sessions = [s for s in sessions if s.complexity_level == complexity_level]

        return sessions

    async def save_session(self, session: SessionContext) -> None:
        """Persist a session to storage.

        This method should be implemented with database persistence
        when the storage layer is integrated.

        Parameters
        ----------
        session : SessionContext
            The session context to persist.

        Raises
        ------
        MoziSessionError
            If session persistence fails.
        """
        try:
            self._sessions[session.session_id] = session
        except Exception as e:
            msg = "Failed to save session"
            raise MoziSessionError(msg, session_id=session.session_id, cause=e) from e

    async def load_session(self, session_id: str) -> SessionContext:
        """Load a session from storage.

        This method should be implemented with database retrieval
        when the storage layer is integrated.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        SessionContext
            The loaded session context.

        Raises
        ------
        MoziSessionError
            If session loading fails or session not found.
        """
        return await self.get_session(session_id)

    async def pause_session(self, session_id: str) -> SessionContext:
        """Pause an active session.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        SessionContext
            The paused session context.

        Raises
        ------
        MoziSessionError
            If session is not found or not in ACTIVE state.
        """
        session = await self.get_session(session_id)

        if session.state != "ACTIVE":
            msg = f"Cannot pause session in state: {session.state}"
            raise MoziSessionError(msg, session_id=session_id)

        session.state = "PAUSED"
        session.updated_at = datetime.now()
        return await self.update_session(session)

    async def resume_session(self, session_id: str) -> SessionContext:
        """Resume a paused session.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        SessionContext
            The resumed session context.

        Raises
        ------
        MoziSessionError
            If session is not found or not in PAUSED state.
        """
        session = await self.get_session(session_id)

        if session.state != "PAUSED":
            msg = f"Cannot resume session in state: {session.state}"
            raise MoziSessionError(msg, session_id=session_id)

        session.state = "ACTIVE"
        session.updated_at = datetime.now()
        return await self.update_session(session)

    async def complete_session(self, session_id: str) -> SessionContext:
        """Mark a session as completed.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        SessionContext
            The completed session context.

        Raises
        ------
        MoziSessionError
            If session is not found.
        """
        session = await self.get_session(session_id)
        session.state = "COMPLETED"
        session.updated_at = datetime.now()
        return await self.update_session(session)

    async def abandon_session(self, session_id: str) -> SessionContext:
        """Mark a session as abandoned.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        SessionContext
            The abandoned session context.

        Raises
        ------
        MoziSessionError
            If session is not found.
        """
        session = await self.get_session(session_id)
        session.state = "ABANDONED"
        session.updated_at = datetime.now()
        return await self.update_session(session)

    def get_active_session_ids(self) -> list[str]:
        """Get IDs of all active sessions.

        Returns
        -------
        list[str]
            List of session IDs with ACTIVE state.
        """
        return [
            session_id
            for session_id, session in self._sessions.items()
            if session.state == "ACTIVE"
        ]

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Parameters
        ----------
        session_id : str
            The unique session identifier.

        Returns
        -------
        bool
            True if session exists, False otherwise.
        """
        return session_id in self._sessions
