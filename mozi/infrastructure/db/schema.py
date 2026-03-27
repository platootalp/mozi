"""Database schema definitions for Mozi.

This module defines the SQLite database schema including tables for:
- sessions: User sessions with state and metadata
- tasks: Tasks associated with sessions
- messages: Conversation messages
- context: Retrieved context for RAG

Schema version is tracked for migrations.
"""

from __future__ import annotations

__all__ = ["SCHEMA_VERSION", "DatabaseSchema", "CREATE_TABLES_SQL", "DROP_TABLES_SQL"]

SCHEMA_VERSION: int = 1


class DatabaseSchema:
    """Database schema manager.

    This class holds the SQL statements for creating and dropping
    all database tables.

    Attributes
    ----------
    version : int
        Current schema version number.
    """

    version: int = SCHEMA_VERSION

    # SQL statement to create all tables
    CREATE_TABLES: str = """
        -- Sessions table: stores user session state
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            complexity_score INTEGER NOT NULL DEFAULT 0,
            complexity_level TEXT NOT NULL DEFAULT 'SIMPLE',
            state TEXT NOT NULL DEFAULT 'ACTIVE',
            metadata TEXT NOT NULL DEFAULT '{}'
        );

        -- Tasks table: stores tasks within sessions
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            parent_id TEXT,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            complexity_score INTEGER NOT NULL DEFAULT 0,
            complexity_level TEXT NOT NULL DEFAULT 'SIMPLE',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            result TEXT,
            error TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE SET NULL
        );

        -- Messages table: stores conversation messages
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            task_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );

        -- Context table: stores retrieved context for RAG
        CREATE TABLE IF NOT EXISTS context (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            task_id TEXT,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            relevance_score REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_tasks_session_id ON tasks(session_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_task_id ON messages(task_id);
        CREATE INDEX IF NOT EXISTS idx_context_session_id ON context(session_id);
        CREATE INDEX IF NOT EXISTS idx_context_task_id ON context(task_id);
    """

    # SQL statement to drop all tables (for testing or migrations)
    DROP_TABLES: str = """
        DROP TABLE IF EXISTS context;
        DROP TABLE IF EXISTS messages;
        DROP TABLE IF EXISTS tasks;
        DROP TABLE IF EXISTS sessions;
    """


# Module-level constants for convenience
CREATE_TABLES_SQL: str = DatabaseSchema.CREATE_TABLES
DROP_TABLES_SQL: str = DatabaseSchema.DROP_TABLES
