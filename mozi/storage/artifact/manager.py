"""Artifact store manager for Mozi.

This module provides async artifact (large file) storage using
SQLite for metadata and filesystem for content.
"""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast


@dataclass
class Artifact:
    """Artifact data model.

    Attributes
    ----------
    id : str
        Unique artifact identifier.
    session_id : str | None
        Associated session ID.
    name : str
        Artifact name.
    file_path : Path
        Path to the artifact file.
    size : int
        File size in bytes.
    content_type : str
        MIME content type.
    created_at : datetime | None
        Creation timestamp.
    """

    id: str
    session_id: str | None
    name: str
    file_path: Path
    size: int
    content_type: str
    created_at: datetime | None = None


class ArtifactStore:
    """Artifact storage manager.

    This class manages artifact storage including file content and
    metadata. Files are stored in the filesystem, metadata in SQLite.

    Attributes
    ----------
    artifact_dir : Path
        Directory for artifact storage.

    Examples
    --------
    Store an artifact:

        store = ArtifactStore(Path("~/.mozi/artifacts"))
        data = b"file content here"
        artifact = await store.store(data, "readme.txt", "sess_123")

    Read an artifact:

        content = await store.read(artifact.id)
    """

    def __init__(self, artifact_dir: Path) -> None:
        """Initialize the artifact store.

        Parameters
        ----------
        artifact_dir : Path
            Directory for storing artifacts.
        """
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the metadata database."""
        conn = sqlite3.connect(self.artifact_dir / "artifacts.db")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                size INTEGER,
                content_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
            """,
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id)",
        )
        conn.close()

    def _sanitize_name(self, name: str) -> str:
        """Sanitize artifact name to prevent path traversal.

        Parameters
        ----------
        name : str
            Original artifact name.

        Returns
        -------
        str
            Sanitized name safe for filesystem use.
        """
        name = name.replace("/", "_").replace("..", "_")
        return name

    async def store(
        self,
        data: bytes,
        name: str,
        session_id: str,
        content_type: str = "application/octet-stream",
    ) -> Artifact:
        """Store an artifact.

        Parameters
        ----------
        data : bytes
            The artifact data to store.
        name : str
            The artifact name.
        session_id : str
            The associated session ID.
        content_type : str
            The MIME content type.

        Returns
        -------
        Artifact
            The created artifact metadata.
        """
        artifact_id = str(uuid.uuid4())
        safe_name = self._sanitize_name(name)
        file_path = self.artifact_dir / f"{artifact_id}_{safe_name}"

        # Write file (sync operation)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._sync_write_file,
            file_path,
            data,
        )

        # Store metadata
        await loop.run_in_executor(
            None,
            self._sync_store_metadata,
            artifact_id,
            session_id,
            name,
            str(file_path),
            len(data),
            content_type,
        )

        return Artifact(
            id=artifact_id,
            session_id=session_id,
            name=name,
            file_path=file_path,
            size=len(data),
            content_type=content_type,
        )

    def _sync_write_file(self, file_path: Path, data: bytes) -> None:
        """Synchronous file write operation.

        Parameters
        ----------
        file_path : Path
            Path to write to.
        data : bytes
            Data to write.
        """
        with open(file_path, "wb") as f:
            f.write(data)

    def _sync_store_metadata(
        self,
        artifact_id: str,
        session_id: str,
        name: str,
        file_path: str,
        size: int,
        content_type: str,
    ) -> None:
        """Synchronous metadata storage.

        Parameters
        ----------
        artifact_id : str
            Unique artifact identifier.
        session_id : str
            Associated session ID.
        name : str
            Artifact name.
        file_path : str
            Path to the stored file.
        size : int
            File size in bytes.
        content_type : str
            MIME content type.
        """
        conn = sqlite3.connect(self.artifact_dir / "artifacts.db")
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, name, file_path, size, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, session_id, name, file_path, size, content_type),
        )
        conn.commit()
        conn.close()

    async def get(self, artifact_id: str) -> Artifact | None:
        """Get artifact metadata by ID.

        Parameters
        ----------
        artifact_id : str
            The artifact ID to retrieve.

        Returns
        -------
        Artifact | None
            The artifact metadata if found, None otherwise.
        """
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, self._sync_get, artifact_id)

        if not row:
            return None

        return Artifact(
            id=row[0],
            session_id=row[1],
            name=row[2],
            file_path=Path(row[3]),
            size=row[4],
            content_type=row[5],
            created_at=datetime.fromisoformat(row[6]) if row[6] else None,
        )

    def _sync_get(self, artifact_id: str) -> tuple[Any, ...] | None:
        """Synchronous get operation.

        Parameters
        ----------
        artifact_id : str
            The artifact ID to retrieve.

        Returns
        -------
        tuple | None
            The database row if found, None otherwise.
        """
        conn = sqlite3.connect(self.artifact_dir / "artifacts.db")
        cursor = conn.execute(
            "SELECT * FROM artifacts WHERE id = ?",
            (artifact_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return row if row is None else cast(tuple[Any, ...], row)

    async def read(self, artifact_id: str) -> bytes | None:
        """Read artifact content.

        Parameters
        ----------
        artifact_id : str
            The artifact ID to read.

        Returns
        -------
        bytes | None
            The artifact content if found, None otherwise.
        """
        artifact = await self.get(artifact_id)
        if not artifact:
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_read_file,
            artifact.file_path,
        )

    def _sync_read_file(self, file_path: Path) -> bytes:
        """Synchronous file read operation.

        Parameters
        ----------
        file_path : Path
            Path to read from.

        Returns
        -------
        bytes
            The file content.
        """
        with open(file_path, "rb") as f:
            return f.read()

    async def delete(self, artifact_id: str) -> bool:
        """Delete an artifact.

        Parameters
        ----------
        artifact_id : str
            The artifact ID to delete.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        artifact = await self.get(artifact_id)
        if not artifact:
            return False

        loop = asyncio.get_event_loop()

        # Delete file
        if artifact.file_path.exists():
            await loop.run_in_executor(None, artifact.file_path.unlink)

        # Delete metadata
        await loop.run_in_executor(
            None,
            self._sync_delete_metadata,
            artifact_id,
        )

        return True

    def _sync_delete_metadata(self, artifact_id: str) -> None:
        """Synchronous metadata deletion.

        Parameters
        ----------
        artifact_id : str
            The artifact ID to delete.
        """
        conn = sqlite3.connect(self.artifact_dir / "artifacts.db")
        conn.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
        conn.commit()
        conn.close()

    async def list_by_session(self, session_id: str) -> list[Artifact]:
        """List all artifacts for a session.

        Parameters
        ----------
        session_id : str
            The session ID to list artifacts for.

        Returns
        -------
        list[Artifact]
            List of artifacts for the session.
        """
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(
            None,
            self._sync_list_by_session,
            session_id,
        )

        return [
            Artifact(
                id=row[0],
                session_id=row[1],
                name=row[2],
                file_path=Path(row[3]),
                size=row[4],
                content_type=row[5],
                created_at=datetime.fromisoformat(row[6]) if row[6] else None,
            )
            for row in rows
        ]

    def _sync_list_by_session(self, session_id: str) -> list[tuple[Any, ...]]:
        """Synchronous list by session operation.

        Parameters
        ----------
        session_id : str
            The session ID to list artifacts for.

        Returns
        -------
        list[tuple]
            List of database rows.
        """
        conn = sqlite3.connect(self.artifact_dir / "artifacts.db")
        cursor = conn.execute(
            "SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
