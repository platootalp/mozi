"""Migration manager for Mozi.

This module provides database migration functionality for
schema evolution and version tracking.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable


class MigrationError(Exception):
    """Exception raised when a migration fails.

    Attributes
    ----------
    message : str
        Error message describing the failure.
    """

    def __init__(self, message: str) -> None:
        """Initialize the migration error.

        Parameters
        ----------
        message : str
            Error message describing the failure.
        """
        self.message = message
        super().__init__(self.message)


# Type alias for migration functions
Migration = Callable[[sqlite3.Connection], None]


class MigrationManager:
    """Database migration manager.

    This class manages database schema migrations with version tracking.

    Attributes
    ----------
    db_path : str
        Path to the SQLite database file.

    Examples
    --------
    Run migrations:

        manager = MigrationManager("/path/to/database.db")
        await manager.migrate()
    """

    def __init__(self, db_path: str) -> None:
        """Initialize the migration manager.

        Parameters
        ----------
        db_path : str
            Path to the SQLite database file.
        """
        self.db_path = db_path

    async def migrate(self) -> None:
        """Execute all pending migrations.

        This method runs all migrations that have not yet been applied.
        """
        loop = __import__("asyncio").get_event_loop()
        await loop.run_in_executor(None, self._sync_migrate)

    def _sync_migrate(self) -> None:
        """Synchronous migration execution."""
        conn = sqlite3.connect(self.db_path)

        # Ensure migrations table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )

        # Get current version
        cursor = conn.execute("SELECT MAX(version) FROM schema_migrations")
        current_version = cursor.fetchone()[0] or 0

        # Execute pending migrations
        for version, migration in MIGRATIONS.items():
            if version > current_version:
                self._apply_migration_sync(conn, version, migration)

        conn.close()

    def _apply_migration_sync(
        self,
        conn: sqlite3.Connection,
        version: int,
        migration: Migration,
    ) -> None:
        """Apply a single migration synchronously.

        Parameters
        ----------
        conn : sqlite3.Connection
            Database connection.
        version : int
            Migration version number.
        migration : Migration
            Migration function to apply.

        Raises
        ------
        MigrationError
            If the migration fails.
        """
        try:
            migration(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            msg = f"Migration {version} failed: {e}"
            raise MigrationError(msg) from e


# Registry of migrations
# Add migrations here as schema evolves
MIGRATIONS: dict[int, Migration] = {}


def register_migration(version: int) -> Callable[[Migration], Migration]:
    """Decorator to register a migration function.

    Parameters
    ----------
    version : int
        Migration version number.

    Returns
    -------
    Callable[[Migration], Migration]
        Decorator function.
    """

    def decorator(func: Migration) -> Migration:
        """Register the migration.

        Parameters
        ----------
        func : Migration
            Migration function to register.

        Returns
        -------
        Migration
            The same function (for chaining).
        """
        MIGRATIONS[version] = func
        return func

    return decorator
