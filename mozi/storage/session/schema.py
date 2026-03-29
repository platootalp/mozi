"""Session schema definitions for Mozi.

This module defines the Session data model and related enums.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SessionStatus(Enum):
    """Session status enumeration.

    Attributes
    ----------
    ACTIVE : str
        Session is currently active.
    COMPLETED : str
        Session has been completed.
    ERROR : str
        Session ended with an error.
    """

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ComplexityLevel(Enum):
    """Task complexity level enumeration.

    Attributes
    ----------
    SIMPLE : str
        Low complexity task (score <= 40).
    MEDIUM : str
        Medium complexity task (score 41-70).
    COMPLEX : str
        High complexity task (score > 70).
    """

    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


@dataclass
class Session:
    """Session data model.

    Attributes
    ----------
    id : str
        Unique session identifier.
    created_at : datetime
        Session creation timestamp.
    updated_at : datetime
        Last update timestamp.
    status : SessionStatus
        Current session status.
    complexity_level : ComplexityLevel | None
        Assessed complexity level.
    complexity_score : int | None
        Numerical complexity score (0-100).
    model : str | None
        Model used for this session.
    message_count : int
        Number of messages in the session.
    metadata : dict[str, Any]
        Additional session metadata.
    last_activity : datetime | None
        Last activity timestamp.
    name : str | None
        Optional human-readable session name.
    """

    id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    complexity_level: ComplexityLevel | None = None
    complexity_score: int | None = None
    model: str | None = None
    message_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    last_activity: datetime | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the session.
        """
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "complexity_level": (self.complexity_level.value if self.complexity_level else None),
            "complexity_score": self.complexity_score,
            "model": self.model,
            "message_count": self.message_count,
            "metadata": self.metadata,
            "last_activity": (self.last_activity.isoformat() if self.last_activity else None),
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Create session from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary representation of a session.

        Returns
        -------
        Session
            Session instance.
        """
        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            status=SessionStatus(data["status"]),
            complexity_level=(
                ComplexityLevel(data["complexity_level"]) if data.get("complexity_level") else None
            ),
            complexity_score=data.get("complexity_score"),
            model=data.get("model"),
            message_count=data.get("message_count", 0),
            metadata=data.get("metadata", {}),
            last_activity=(
                datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None
            ),
            name=data.get("name"),
        )


# SQL for session table creation
CREATE_SESSIONS_TABLE: str = """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL,
        complexity_level TEXT,
        complexity_score INTEGER,
        model TEXT,
        message_count INTEGER DEFAULT 0,
        metadata JSON,
        last_activity TIMESTAMP,
        name TEXT
    )
"""

CREATE_SESSIONS_INDEXES: str = """
    CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
    CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);
    CREATE INDEX IF NOT EXISTS idx_sessions_name ON sessions(name);
"""
