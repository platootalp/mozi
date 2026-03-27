"""Tests for mozi.infrastructure.db module.

This module contains unit tests for the SQLite database layer.
Uses in-memory database for isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from mozi.core.error import MoziRuntimeError
from mozi.infrastructure.db import (
    DatabaseSchema,
    SCHEMA_VERSION,
    SQLiteDB,
    get_db_path,
)
from mozi.infrastructure.db.schema import CREATE_TABLES_SQL, DROP_TABLES_SQL


class TestDatabaseSchema:
    """Tests for DatabaseSchema class."""

    def test_schema_version(self) -> None:
        """Test schema version is set correctly."""
        assert SCHEMA_VERSION == 1
        assert DatabaseSchema.version == 1

    def test_create_tables_sql_not_empty(self) -> None:
        """Test CREATE_TABLES_SQL contains required statements."""
        sql = CREATE_TABLES_SQL
        assert "CREATE TABLE IF NOT EXISTS sessions" in sql
        assert "CREATE TABLE IF NOT EXISTS tasks" in sql
        assert "CREATE TABLE IF NOT EXISTS messages" in sql
        assert "CREATE TABLE IF NOT EXISTS context" in sql

    def test_create_tables_sql_has_indexes(self) -> None:
        """Test CREATE_TABLES_SQL contains index definitions."""
        sql = CREATE_TABLES_SQL
        assert "CREATE INDEX IF NOT EXISTS idx_tasks_session_id" in sql
        assert "CREATE INDEX IF NOT EXISTS idx_messages_session_id" in sql
        assert "CREATE INDEX IF NOT EXISTS idx_context_session_id" in sql

    def test_drop_tables_sql_drops_all_tables(self) -> None:
        """Test DROP_TABLES_SQL contains drop statements."""
        sql = DROP_TABLES_SQL
        assert "DROP TABLE IF EXISTS sessions" in sql
        assert "DROP TABLE IF EXISTS tasks" in sql
        assert "DROP TABLE IF EXISTS messages" in sql
        assert "DROP TABLE IF EXISTS context" in sql


@pytest.mark.unit
class TestSQLiteDBInit:
    """Tests for SQLiteDB initialization."""

    def test_init_with_memory_db(self) -> None:
        """Test initialization with in-memory database."""
        db = SQLiteDB(":memory:")
        assert db.db_path == ":memory:"
        assert db.connection is None

    def test_init_with_file_path(self) -> None:
        """Test initialization with file path."""
        db = SQLiteDB("/tmp/test_mozi.db")
        assert db.db_path == "/tmp/test_mozi.db"
        assert db.connection is None

    def test_init_with_custom_schema(self) -> None:
        """Test initialization with custom schema."""
        schema = DatabaseSchema()
        db = SQLiteDB(":memory:", schema=schema)
        assert db._schema is schema


@pytest.mark.unit
class TestSQLiteDBInitialize:
    """Tests for SQLiteDB.initialize()."""

    @pytest.mark.asyncio
    async def test_init_creates_connection(self) -> None:
        """Test initialize creates database connection."""
        db = SQLiteDB(":memory:")
        await db.initialize()
        assert db.connection is not None
        await db.close()

    @pytest.mark.asyncio
    async def test_init_creates_tables(self) -> None:
        """Test initialize creates all tables."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        # Verify sessions table exists
        result = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert len(result) == 1

        await db.close()

    @pytest.mark.asyncio
    async def test_init_creates_all_tables(self) -> None:
        """Test initialize creates all schema tables."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        tables = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [row["name"] for row in tables]

        assert "sessions" in table_names
        assert "tasks" in table_names
        assert "messages" in table_names
        assert "context" in table_names

        await db.close()

    @pytest.mark.asyncio
    async def test_init_creates_indexes(self) -> None:
        """Test initialize creates indexes."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        indexes = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        index_names = [row["name"] for row in indexes]

        assert "idx_tasks_session_id" in index_names
        assert "idx_tasks_parent_id" in index_names
        assert "idx_messages_session_id" in index_names
        assert "idx_context_session_id" in index_names

        await db.close()


@pytest.mark.unit
class TestSQLiteDBClose:
    """Tests for SQLiteDB.close()."""

    @pytest.mark.asyncio
    async def test_close_without_init(self) -> None:
        """Test close without prior initialization does not raise."""
        db = SQLiteDB(":memory:")
        await db.close()  # Should not raise
        assert db.connection is None

    @pytest.mark.asyncio
    async def test_close_after_init(self) -> None:
        """Test close after initialization sets connection to None."""
        db = SQLiteDB(":memory:")
        await db.initialize()
        assert db.connection is not None

        await db.close()
        assert db.connection is None


@pytest.mark.unit
class TestSQLiteDBExecute:
    """Tests for SQLiteDB.execute()."""

    @pytest.mark.asyncio
    async def test_execute_without_init_raises(self) -> None:
        """Test execute without initialization raises MoziRuntimeError."""
        db = SQLiteDB(":memory:")
        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.execute("SELECT 1")

        assert "Database not initialized" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_execute_insert(self) -> None:
        """Test execute with INSERT statement."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        cursor = await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )
        assert cursor.rowcount == 1

        await db.close()

    @pytest.mark.asyncio
    async def test_execute_with_no_parameters(self) -> None:
        """Test execute with query that has no parameters."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        cursor = await db.execute("SELECT 1 as id")
        row = await cursor.fetchone()
        assert row[0] == 1

        await db.close()

    @pytest.mark.asyncio
    async def test_execute_many(self) -> None:
        """Test execute_many with multiple inserts."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )

        await db.execute_many(
            "INSERT INTO tasks (id, session_id, description, status, complexity_score, "
            "complexity_level, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("task1", "sess1", "Task 1", "PENDING", 10, "SIMPLE", "2026-03-27T10:00:00", "2026-03-27T10:00:00"),
                ("task2", "sess1", "Task 2", "PENDING", 10, "SIMPLE", "2026-03-27T10:00:00", "2026-03-27T10:00:00"),
            ],
        )

        rows = await db.fetchall("SELECT id, description FROM tasks ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["id"] == "task1"
        assert rows[1]["id"] == "task2"

        await db.close()


@pytest.mark.unit
class TestSQLiteDBFetch:
    """Tests for SQLiteDB.fetchall() and fetchone()."""

    @pytest.mark.asyncio
    async def test_fetchall_without_init_raises(self) -> None:
        """Test fetchall without initialization raises MoziRuntimeError."""
        db = SQLiteDB(":memory:")
        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.fetchall("SELECT 1")

        assert "Database not initialized" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_fetchone_without_init_raises(self) -> None:
        """Test fetchone without initialization raises MoziRuntimeError."""
        db = SQLiteDB(":memory:")
        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.fetchone("SELECT 1")

        assert "Database not initialized" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_fetchall_empty_result(self) -> None:
        """Test fetchall with no matching rows returns empty list."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        result = await db.fetchall("SELECT * FROM sessions WHERE id = ?", ("nonexistent",))
        assert result == []

        await db.close()

    @pytest.mark.asyncio
    async def test_fetchone_empty_result(self) -> None:
        """Test fetchone with no matching rows returns None."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        result = await db.fetchone("SELECT * FROM sessions WHERE id = ?", ("nonexistent",))
        assert result is None

        await db.close()

    @pytest.mark.asyncio
    async def test_fetchall_with_data(self) -> None:
        """Test fetchall returns all matching rows."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        # Insert test data
        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )
        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess2", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 75, "COMPLEX", "ACTIVE", "{}"),
        )
        await db.commit()

        result = await db.fetchall("SELECT id, complexity_level FROM sessions ORDER BY id")
        assert len(result) == 2
        assert result[0]["id"] == "sess1"
        assert result[0]["complexity_level"] == "SIMPLE"
        assert result[1]["id"] == "sess2"
        assert result[1]["complexity_level"] == "COMPLEX"

        await db.close()

    @pytest.mark.asyncio
    async def test_fetchone_returns_single_row(self) -> None:
        """Test fetchone returns only the first row."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        # Insert multiple rows
        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )
        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess2", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 75, "COMPLEX", "ACTIVE", "{}"),
        )
        await db.commit()

        result = await db.fetchone("SELECT id FROM sessions ORDER BY id")
        assert result is not None
        assert result["id"] == "sess1"

        await db.close()


@pytest.mark.unit
class TestSQLiteDBTransaction:
    """Tests for SQLiteDB transaction methods."""

    @pytest.mark.asyncio
    async def test_commit_without_init_raises(self) -> None:
        """Test commit without initialization raises MoziRuntimeError."""
        db = SQLiteDB(":memory:")
        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.commit()

        assert "Database not initialized" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_rollback_without_init_raises(self) -> None:
        """Test rollback without initialization raises MoziRuntimeError."""
        db = SQLiteDB(":memory:")
        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.rollback()

        assert "Database not initialized" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_commit_persists_changes(self) -> None:
        """Test commit persists changes to database."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )
        await db.commit()

        # Create new connection to verify persistence
        db2 = SQLiteDB(":memory:")
        await db2.initialize()
        await db2.execute("ATTACH DATABASE ':memory:' AS attached")

        result = await db.fetchone("SELECT id FROM sessions WHERE id = ?", ("sess1",))
        assert result is not None
        assert result["id"] == "sess1"

        await db.close()
        await db2.close()

    @pytest.mark.asyncio
    async def test_rollback_reverts_changes(self) -> None:
        """Test rollback reverts uncommitted changes."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )
        await db.commit()

        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess2", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 75, "COMPLEX", "ACTIVE", "{}"),
        )
        # Rollback without committing
        await db.rollback()

        result = await db.fetchall("SELECT id FROM sessions ORDER BY id")
        assert len(result) == 1
        assert result[0]["id"] == "sess1"

        await db.close()


@pytest.mark.unit
class TestSQLiteDBContextManager:
    """Tests for SQLiteDB async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_initializes_and_closes(self) -> None:
        """Test context manager initializes and closes database."""
        async with SQLiteDB(":memory:") as db:
            assert db.connection is not None
            # Can execute queries
            cursor = await db.execute("SELECT 1 as id")
            row = await cursor.fetchone()
            assert row[0] == 1

        # After exiting context, connection should be closed
        assert db.connection is None

    @pytest.mark.asyncio
    async def test_context_manager_rollback_on_exception(self) -> None:
        """Test context manager rolls back on exception."""
        db = SQLiteDB(":memory:")
        await db.initialize()

        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, complexity_score, "
            "complexity_level, state, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("sess1", "2026-03-27T10:00:00", "2026-03-27T10:00:00", 25, "SIMPLE", "ACTIVE", "{}"),
        )

        async with db:
            # Inside context, exception triggers rollback
            pass  # No exception

        await db.close()


@pytest.mark.unit
class TestGetDbPath:
    """Tests for get_db_path function."""

    def test_get_db_path_with_custom_base(self) -> None:
        """Test get_db_path with custom base directory."""
        result = get_db_path("/tmp/mozi_test")
        assert result == "/tmp/mozi_test/mozi.db"

    def test_get_db_path_returns_string(self) -> None:
        """Test get_db_path returns a string path."""
        result = get_db_path()
        assert isinstance(result, str)
        assert result.endswith("mozi.db")


@pytest.mark.unit
class TestModuleExports:
    """Tests for module-level exports."""

    def test_sqlite_db_importable(self) -> None:
        """Test SQLiteDB is importable from module."""
        from mozi.infrastructure.db import SQLiteDB
        assert SQLiteDB is not None

    def test_schema_importable(self) -> None:
        """Test DatabaseSchema is importable from module."""
        from mozi.infrastructure.db import DatabaseSchema
        assert DatabaseSchema is not None

    def test_get_db_path_importable(self) -> None:
        """Test get_db_path is importable from module."""
        from mozi.infrastructure.db import get_db_path
        assert get_db_path is not None


@pytest.mark.unit
class TestSQLiteDBExceptionHandlers:
    """Tests for SQLiteDB exception handlers."""

    @pytest.mark.asyncio
    async def test_initialize_connect_raises(self) -> None:
        """Test initialize handles connection error."""
        db = SQLiteDB(":memory:")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = aiosqlite.Error("Connection failed")

            with pytest.raises(MoziRuntimeError) as exc_info:
                await db.initialize()

            assert "Failed to initialize database" in str(exc_info.value.message)
            assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_initialize_executescript_raises(self) -> None:
        """Test initialize handles executescript error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_conn.row_factory = aiosqlite.Row
        mock_conn.executescript = AsyncMock(side_effect=aiosqlite.Error("Script failed"))
        mock_conn.close = AsyncMock()

        with patch("aiosqlite.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn

            with pytest.raises(MoziRuntimeError) as exc_info:
                await db.initialize()

            assert "Failed to initialize database" in str(exc_info.value.message)
            assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_close_raises(self) -> None:
        """Test close handles connection close error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_conn.close = AsyncMock(side_effect=aiosqlite.Error("Close failed"))
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.close()

        assert "Failed to close database connection" in str(exc_info.value.message)
        assert exc_info.value.cause is not None
        assert db.connection is None

    @pytest.mark.asyncio
    async def test_execute_raises(self) -> None:
        """Test execute handles query error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Query failed"))
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.execute("SELECT 1")

        assert "Failed to execute query" in str(exc_info.value.message)
        assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_execute_many_raises(self) -> None:
        """Test execute_many handles error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_conn.executemany = AsyncMock(side_effect=aiosqlite.Error("Many failed"))
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.execute_many("SELECT 1", [])

        assert "Failed to execute many" in str(exc_info.value.message)
        assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_fetchall_raises(self) -> None:
        """Test fetchall handles query error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_cursor = MagicMock()
        mock_cursor.fetchall = AsyncMock(side_effect=aiosqlite.Error("Fetchall failed"))
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.fetchall("SELECT 1")

        assert "Failed to fetchall" in str(exc_info.value.message)
        assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_fetchone_raises(self) -> None:
        """Test fetchone handles query error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_cursor = MagicMock()
        mock_cursor.fetchone = AsyncMock(side_effect=aiosqlite.Error("Fetchone failed"))
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.fetchone("SELECT 1")

        assert "Failed to fetchone" in str(exc_info.value.message)
        assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_commit_raises(self) -> None:
        """Test commit handles error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_conn.commit = AsyncMock(side_effect=aiosqlite.Error("Commit failed"))
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.commit()

        assert "Failed to commit transaction" in str(exc_info.value.message)
        assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_rollback_raises(self) -> None:
        """Test rollback handles error."""
        db = SQLiteDB(":memory:")
        mock_conn = MagicMock(spec=aiosqlite.Connection)
        mock_conn.rollback = AsyncMock(side_effect=aiosqlite.Error("Rollback failed"))
        db.connection = mock_conn

        with pytest.raises(MoziRuntimeError) as exc_info:
            await db.rollback()

        assert "Failed to rollback transaction" in str(exc_info.value.message)
        assert exc_info.value.cause is not None
