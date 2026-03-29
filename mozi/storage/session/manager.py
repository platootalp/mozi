"""Session store manager for Mozi.

This module provides async session persistence using SQLite.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Any, cast

from mozi.storage.base import BaseStore
from mozi.storage.session.schema import (
    CREATE_SESSIONS_INDEXES,
    CREATE_SESSIONS_TABLE,
    ComplexityLevel,
    Session,
    SessionStatus,
)


class SessionStore(BaseStore[Session]):
    """Session storage manager.

    This class manages session persistence including create, read,
    update, delete, and list operations.

    Attributes
    ----------
    db_path : str
        Path to the SQLite database file.

    Examples
    --------
    Create a new session:

        store = SessionStore("/path/to/sessions.db")
        session = Session(
            id="sess_123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=SessionStatus.ACTIVE,
        )
        await store.create(session)

    Get an existing session:

        session = await store.get("sess_123")
    """

    def __init__(self, db_path: str) -> None:
        """Initialize the session store.

        Parameters
        ----------
        db_path : str
            Path to the SQLite database file.
        """
        super().__init__(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(CREATE_SESSIONS_TABLE)
        for statement in CREATE_SESSIONS_INDEXES.strip().split(";"):
            if statement.strip():
                conn.execute(statement)
        conn.commit()
        conn.close()

    async def create(self, session: Session) -> Session:
        """Create a new session.

        Parameters
        ----------
        session : Session
            The session to create.

        Returns
        -------
        Session
            The created session.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_create, session)
        return session

    def _sync_create(self, session: Session) -> None:
        """Synchronous create operation.

        Parameters
        ----------
        session : Session
            The session to create.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO sessions
                (id, status, complexity_level, complexity_score, model, metadata, name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.status.value,
                session.complexity_level.value if session.complexity_level else None,
                session.complexity_score,
                session.model,
                json.dumps(session.metadata or {}),
                session.name,
            ),
        )
        conn.commit()
        conn.close()

    async def get(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Parameters
        ----------
        session_id : str
            The session ID to retrieve.

        Returns
        -------
        Session | None
            The session if found, None otherwise.
        """
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, self._sync_get, session_id)

        if not row:
            return None

        return self._row_to_session(row)

    def _sync_get(self, session_id: str) -> tuple[Any, ...] | None:
        """Synchronous get operation.

        Parameters
        ----------
        session_id : str
            The session ID to retrieve.

        Returns
        -------
        tuple | None
            The database row if found, None otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return row if row is None else cast(tuple[Any, ...], row)

    async def update(self, session: Session) -> Session:
        """Update an existing session.

        Parameters
        ----------
        session : Session
            The session to update.

        Returns
        -------
        Session
            The updated session.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_update, session)
        return session

    def _sync_update(self, session: Session) -> None:
        """Synchronous update operation.

        Parameters
        ----------
        session : Session
            The session to update.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, complexity_level = ?, complexity_score = ?,
                model = ?, message_count = ?, metadata = ?, name = ?,
                last_activity = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                session.status.value,
                session.complexity_level.value if session.complexity_level else None,
                session.complexity_score,
                session.model,
                session.message_count,
                json.dumps(session.metadata or {}),
                session.name,
                session.id,
            ),
        )
        conn.commit()
        conn.close()

    async def list_sessions(
        self,
        limit: int = 10,
        status: SessionStatus | None = None,
    ) -> list[Session]:
        """List sessions with optional filtering.

        Parameters
        ----------
        limit : int
            Maximum number of sessions to return.
        status : SessionStatus | None
            Filter by session status.

        Returns
        -------
        list[Session]
            List of matching sessions.
        """
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, self._sync_list, limit, status)
        return [self._row_to_session(row) for row in rows]

    def _sync_list(
        self,
        limit: int,
        status: SessionStatus | None = None,
    ) -> list[tuple[Any, ...]]:
        """Synchronous list operation.

        Parameters
        ----------
        limit : int
            Maximum number of sessions to return.
        status : SessionStatus | None
            Filter by session status.

        Returns
        -------
        list[tuple]
            List of database rows.
        """
        conn = sqlite3.connect(self.db_path)

        if status:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (status.value, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()
        return rows

    async def delete(self, session_id: str) -> bool:
        """Delete a session by ID.

        Parameters
        ----------
        session_id : str
            The session ID to delete.

        Returns
        -------
        bool
            True if the session was deleted, False if not found.
        """
        loop = asyncio.get_event_loop()
        deleted = await loop.run_in_executor(None, self._sync_delete, session_id)
        return deleted

    def _sync_delete(self, session_id: str) -> bool:
        """Synchronous delete operation.

        Parameters
        ----------
        session_id : str
            The session ID to delete.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    async def get_active(self) -> Session | None:
        """Get the most recent active session.

        Returns
        -------
        Session | None
            The most recent active session, or None if no active sessions.
        """
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, self._sync_get_active)

        if not row:
            return None

        return self._row_to_session(row)

    def _sync_get_active(self) -> tuple[Any, ...] | None:
        """Synchronous get active operation.

        Returns
        -------
        tuple | None
            The most recent active session row, or None.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT * FROM sessions
            WHERE status = 'ACTIVE'
            ORDER BY last_activity DESC
            LIMIT 1
            """,
        )
        row = cursor.fetchone()
        conn.close()
        return row if row is None else cast(tuple[Any, ...], row)

    async def list(
        self,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[Session]:
        """List sessions with optional filtering.

        Parameters
        ----------
        limit : int
            Maximum number of sessions to return.
        **kwargs : Any
            Additional filter parameters (unused for now).

        Returns
        -------
        list[Session]
            List of sessions.
        """
        return await self.list_sessions(limit=limit)

    async def get_by_name(self, name: str) -> Session | None:
        """Get a session by name.

        Parameters
        ----------
        name : str
            The session name to search for.

        Returns
        -------
        Session | None
            The session if found, None otherwise.
        """
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, self._sync_get_by_name, name)

        if not row:
            return None

        return self._row_to_session(row)

    def _sync_get_by_name(self, name: str) -> tuple[Any, ...] | None:
        """Synchronous get by name operation.

        Parameters
        ----------
        name : str
            The session name to retrieve.

        Returns
        -------
        tuple | None
            The database row if found, None otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, created_at, updated_at, status, complexity_level, complexity_score, model, message_count, metadata, last_activity, name FROM sessions WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        conn.close()
        return row if row is None else cast(tuple[Any, ...], row)

    def _row_to_session(self, row: tuple[Any, ...]) -> Session:
        """Convert a database row to a Session object.

        Parameters
        ----------
        row : tuple
            The database row.

        Returns
        -------
        Session
            The Session object.
        """
        return Session(
            id=row[0],
            created_at=datetime.fromisoformat(row[1]),
            updated_at=datetime.fromisoformat(row[2]),
            status=SessionStatus(row[3]),
            complexity_level=ComplexityLevel(row[4]) if row[4] else None,
            complexity_score=row[5],
            model=row[6],
            message_count=row[7],
            metadata=json.loads(row[8]) if row[8] else {},
            last_activity=datetime.fromisoformat(row[9]) if row[9] else None,
            name=row[10] if len(row) > 10 else None,
        )
