"""Database infrastructure module for Mozi.

This module provides SQLite database operations for the Mozi AI Coding Agent.
It uses aiosqlite for async database access.

Examples
--------
Create a database connection:

    db = SQLiteDB(":memory:")
    await db.initialize()
    # use database
    await db.close()

Execute a query:

    result = await db.execute("SELECT * FROM sessions WHERE id = ?", ("sess123",))
"""

from __future__ import annotations

from mozi.infrastructure.db.schema import SCHEMA_VERSION, DatabaseSchema
from mozi.infrastructure.db.sqlite import SQLiteDB, get_db_path

__all__ = [
    "DatabaseSchema",
    "SCHEMA_VERSION",
    "SQLiteDB",
    "get_db_path",
]

__version__: str = "0.1.0"
