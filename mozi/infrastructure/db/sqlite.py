"""Async SQLite database operations for Mozi.

This module provides async database operations using aiosqlite.
It supports sessions, tasks, messages, and context storage.

Examples
--------
Create and initialize a database:

    db = SQLiteDB("data/mozi.db")
    await db.initialize()

Insert a session:

    await db.execute(
        "INSERT INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
        ("sess123", "2026-03-27T10:00:00", "2026-03-27T10:00:00")
    )

Query sessions:

    rows = await db.fetchall("SELECT * FROM sessions WHERE state = ?", ("ACTIVE",))
    row = await db.fetchone("SELECT * FROM sessions WHERE id = ?", ("sess123",))

Close database:

    await db.close()
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import aiosqlite

from mozi.core.error import MoziRuntimeError
from mozi.infrastructure.db.schema import DatabaseSchema


class SQLiteDB:
    """Async SQLite database wrapper.

    This class provides async database operations with aiosqlite.
    It handles connection management, transaction control, and
    provides convenient fetch methods.

    Attributes
    ----------
    db_path : str
        Path to the SQLite database file.
    connection : aiosqlite.Connection | None
        The active database connection, if initialized.

    Examples
    --------
    Use with async context manager:

        async with SQLiteDB(":memory:") as db:
            await db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            await db.execute("INSERT INTO test VALUES (1)")
            rows = await db.fetchall("SELECT * FROM test")
    """

    def __init__(
        self,
        db_path: str,
        schema: DatabaseSchema | None = None,
    ) -> None:
        """Initialize SQLiteDB with path to database file.

        Parameters
        ----------
        db_path : str
            Path to the SQLite database file. Use ":memory:" for
            an in-memory database.
        schema : DatabaseSchema | None, optional
            Schema manager instance. Uses default if not provided.
        """
        self.db_path: str = db_path
        self.connection: aiosqlite.Connection | None = None
        self._schema: DatabaseSchema = schema or DatabaseSchema()

    async def initialize(self) -> None:
        """Initialize database connection and create tables.

        This method opens the database connection and creates all tables
        defined in the schema.

        Raises
        ------
        MoziRuntimeError
            If the database connection fails or schema creation fails.
        """
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row
            await self.connection.executescript(self._schema.CREATE_TABLES)
            await self.connection.commit()
        except aiosqlite.Error as e:
            msg = f"Failed to initialize database at {self.db_path}"
            raise MoziRuntimeError(msg, cause=e) from e

    async def close(self) -> None:
        """Close the database connection.

        This method closes the database connection. After calling,
        database operations will raise an error.

        Raises
        ------
        MoziRuntimeError
            If closing the connection fails.
        """
        if self.connection is not None:
            try:
                await self.connection.close()
            except aiosqlite.Error as e:
                msg = "Failed to close database connection"
                raise MoziRuntimeError(msg, cause=e) from e
            finally:
                self.connection = None

    async def execute(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
    ) -> aiosqlite.Cursor:
        """Execute a SQL query.

        Parameters
        ----------
        query : str
            SQL query to execute. Use ? for parameter placeholders.
        parameters : Sequence[Any] | None, optional
            Parameters to bind to the query.

        Returns
        -------
        aiosqlite.Cursor
            The cursor after executing the query.

        Raises
        ------
        MoziRuntimeError
            If execution fails or database is not initialized.
        """
        if self.connection is None:
            msg = "Database not initialized. Call initialize() first."
            raise MoziRuntimeError(msg)

        try:
            return await self.connection.execute(query, parameters or ())
        except aiosqlite.Error as e:
            msg = f"Failed to execute query: {query[:50]}..."
            raise MoziRuntimeError(msg, cause=e) from e

    async def execute_many(
        self,
        query: str,
        parameters_seq: Sequence[Sequence[Any]],
    ) -> None:
        """Execute a SQL query with multiple parameter sets.

        Parameters
        ----------
        query : str
            SQL query to execute. Use ? for parameter placeholders.
        parameters_seq : Sequence[Sequence[Any]]
            Sequence of parameter sets to bind to the query.

        Raises
        ------
        MoziRuntimeError
            If execution fails or database is not initialized.
        """
        if self.connection is None:
            msg = "Database not initialized. Call initialize() first."
            raise MoziRuntimeError(msg)

        try:
            await self.connection.executemany(query, parameters_seq)
        except aiosqlite.Error as e:
            msg = f"Failed to execute many: {query[:50]}..."
            raise MoziRuntimeError(msg, cause=e) from e

    async def fetchall(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all rows from a query.

        Parameters
        ----------
        query : str
            SQL query to execute. Use ? for parameter placeholders.
        parameters : Sequence[Any] | None, optional
            Parameters to bind to the query.

        Returns
        -------
        list[dict[str, Any]]
            List of rows as dictionaries.

        Raises
        ------
        MoziRuntimeError
            If query fails or database is not initialized.
        """
        if self.connection is None:
            msg = "Database not initialized. Call initialize() first."
            raise MoziRuntimeError(msg)

        try:
            cursor = await self.connection.execute(query, parameters or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except aiosqlite.Error as e:
            msg = f"Failed to fetchall: {query[:50]}..."
            raise MoziRuntimeError(msg, cause=e) from e

    async def fetchone(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch a single row from a query.

        Parameters
        ----------
        query : str
            SQL query to execute. Use ? for parameter placeholders.
        parameters : Sequence[Any] | None, optional
            Parameters to bind to the query.

        Returns
        -------
        dict[str, Any] | None
            A row as a dictionary, or None if no row found.

        Raises
        ------
        MoziRuntimeError
            If query fails or database is not initialized.
        """
        if self.connection is None:
            msg = "Database not initialized. Call initialize() first."
            raise MoziRuntimeError(msg)

        try:
            cursor = await self.connection.execute(query, parameters or ())
            row = await cursor.fetchone()
            return dict(row) if row else None
        except aiosqlite.Error as e:
            msg = f"Failed to fetchone: {query[:50]}..."
            raise MoziRuntimeError(msg, cause=e) from e

    async def commit(self) -> None:
        """Commit the current transaction.

        Raises
        ------
        MoziRuntimeError
            If commit fails or database is not initialized.
        """
        if self.connection is None:
            msg = "Database not initialized. Call initialize() first."
            raise MoziRuntimeError(msg)

        try:
            await self.connection.commit()
        except aiosqlite.Error as e:
            msg = "Failed to commit transaction"
            raise MoziRuntimeError(msg, cause=e) from e

    async def rollback(self) -> None:
        """Rollback the current transaction.

        Raises
        ------
        MoziRuntimeError
            If rollback fails or database is not initialized.
        """
        if self.connection is None:
            msg = "Database not initialized. Call initialize() first."
            raise MoziRuntimeError(msg)

        try:
            await self.connection.rollback()
        except aiosqlite.Error as e:
            msg = "Failed to rollback transaction"
            raise MoziRuntimeError(msg, cause=e) from e

    async def __aenter__(self) -> SQLiteDB:
        """Enter async context manager.

        Returns
        -------
        SQLiteDB
            The database instance.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Parameters
        ----------
        exc_type : Any
            Exception type if an exception was raised.
        exc_val : Any
            Exception value if an exception was raised.
        exc_tb : Any
            Exception traceback if an exception was raised.
        """
        if exc_type is not None and self.connection is not None:
            await self.rollback()
        await self.close()


def get_db_path(base_dir: str | None = None) -> str:
    """Get the path to the Mozi database file.

    Parameters
    ----------
    base_dir : str | None, optional
        Base directory for the database. If None, uses the user's
        data directory (~/Library/Application Support/mozi on macOS,
        ~/.local/share/mozi on Linux).

    Returns
    -------
    str
        Path to the database file.

    Examples
    --------
    Get default path:

        db_path = get_db_path()

    Get path in custom directory:

        db_path = get_db_path("/var/lib/mozi")
    """
    if base_dir is not None:
        return os.path.join(base_dir, "mozi.db")

    home = Path.home()
    if os.uname().sysname == "Darwin":
        app_support = home / "Library" / "Application Support" / "mozi"
    else:
        app_support = home / ".local" / "share" / "mozi"

    app_support.mkdir(parents=True, exist_ok=True)
    return str(app_support / "mozi.db")
