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
from typing import TYPE_CHECKING, Any

from mozi.core.error import MoziSessionError
from mozi.orchestrator.session.context import (
    ComplexityLevel,
    SessionContext,
    SessionState,
)

if TYPE_CHECKING:
    from mozi.orchestrator.session.compactor import ContextCompactor
    from mozi.orchestrator.session.models import SessionMessage
    from mozi.storage.session.file_storage import FileSessionStorage


class SessionManager:
    """Manages session lifecycle.

    This class provides async methods for creating, retrieving, updating,
    and deleting sessions. It uses the database layer for persistence.

    Attributes
    ----------
    _sessions : dict[str, SessionContext]
        In-memory cache of active sessions.
    _storage : FileSessionStorage | None
        File storage for persisting messages.
    _compactor : ContextCompactor | None
        Context compactor for managing context window.

    Examples
    --------
    Create and use a session manager:

        manager = SessionManager()
        session = await manager.create_session(complexity_score=50)
        await manager.save_session(session)

    Create with storage and compactor integration:

        storage = FileSessionStorage("/tmp/sessions")
        compactor = ContextCompactor(context_limit=100000)
        manager = SessionManager(storage=storage, compactor=compactor)
        session = await manager.create_session(complexity_score=50)
    """

    def __init__(
        self,
        storage: FileSessionStorage | None = None,
        compactor: ContextCompactor | None = None,
    ) -> None:
        """Initialize the session manager.

        Parameters
        ----------
        storage : FileSessionStorage | None, optional
            File storage for persisting messages. Defaults to None.
        compactor : ContextCompactor | None, optional
            Context compactor for managing context window. Defaults to None.
        """
        self._sessions: dict[str, SessionContext] = {}
        self._storage = storage
        self._compactor = compactor

    async def create_session(
        self,
        complexity_score: int = 0,
        complexity_level: ComplexityLevel = ComplexityLevel.SIMPLE,
        metadata: dict[str, Any] | None = None,
    ) -> SessionContext:
        """Create a new session.

        Parameters
        ----------
        complexity_score : int, optional
            Initial complexity score (0-100). Defaults to 0.
        complexity_level : ComplexityLevel, optional
            Initial complexity level. Defaults to ComplexityLevel.SIMPLE.
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
                state=SessionState.ACTIVE,
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
        state: SessionState | None = None,
        complexity_level: ComplexityLevel | None = None,
    ) -> list[SessionContext]:
        """List sessions with optional filtering.

        Parameters
        ----------
        state : SessionState | None, optional
            Filter by session state (e.g., SessionState.ACTIVE).
        complexity_level : ComplexityLevel | None, optional
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

        if session.state != SessionState.ACTIVE:
            msg = f"Cannot pause session in state: {session.state}"
            raise MoziSessionError(msg, session_id=session_id)

        session.state = SessionState.PAUSED
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

        if session.state != SessionState.PAUSED:
            msg = f"Cannot resume session in state: {session.state}"
            raise MoziSessionError(msg, session_id=session_id)

        session.state = SessionState.ACTIVE
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
        session.state = SessionState.COMPLETED
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
        session.state = SessionState.ABANDONED
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
            if session.state == SessionState.ACTIVE
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

    async def add_message(
        self, session_id: str, message: SessionMessage
    ) -> SessionContext:
        """Add a message to a session.

        This method appends the message to file storage, updates session
        metadata (message_count, total_tokens), and triggers compaction
        when the context window threshold is reached.

        Parameters
        ----------
        session_id : str
            The unique session identifier.
        message : SessionMessage
            The message to add to the session.

        Returns
        -------
        SessionContext
            The updated session context.

        Raises
        ------
        MoziSessionError
            If session is not found or if storage operations fail.
        """
        try:
            session = await self.get_session(session_id)

            # Append message to file storage if storage is configured
            if self._storage is not None:
                await self._storage.append_message(session_id, message)

            # Update session metadata
            message_count = session.get_metadata("message_count", 0) + 1
            total_tokens = session.get_metadata("total_tokens", 0) + message.tokens
            session.update_metadata("message_count", message_count)
            session.update_metadata("total_tokens", total_tokens)
            session.updated_at = datetime.now()

            # Trigger compaction if threshold is reached
            if self._compactor is not None and self._storage is not None:
                messages = await self._storage.load_messages(session_id)
                if self._compactor.should_compact(messages):
                    compaction_result = await self._compactor.compact(messages)
                    await self._storage.overwrite_messages(
                        session_id, compaction_result.messages
                    )
                    session.update_metadata(
                        "last_compaction_result",
                        {
                            "original_count": compaction_result.original_count,
                            "compacted_count": compaction_result.compacted_count,
                            "original_tokens": compaction_result.original_tokens,
                            "compacted_tokens": compaction_result.compacted_tokens,
                        },
                    )

            self._sessions[session_id] = session
            return session

        except MoziSessionError:
            raise
        except Exception as e:
            msg = "Failed to add message to session"
            raise MoziSessionError(msg, session_id=session_id, cause=e) from e
