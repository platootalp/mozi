"""Session context for Mozi AI Coding Agent.

This module defines the SessionContext dataclass that holds session state
including complexity assessment, task history, and metadata.

Examples
--------
Create a session context:

    ctx = SessionContext(
        session_id="sess_abc123",
        complexity_score=35,
        complexity_level=ComplexityLevel.SIMPLE,
    )

Access session metadata:

    ctx.metadata["user_id"] = "user_123"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ComplexityLevel(Enum):
    """Complexity level for tasks and sessions.

    Attributes
    ----------
    SIMPLE : str
        Tasks with complexity score <= 40.
    MEDIUM : str
        Tasks with complexity score 41-70.
    COMPLEX : str
        Tasks with complexity score > 70.
    """

    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


class SessionState(Enum):
    """State of a session.

    Attributes
    ----------
    ACTIVE : str
        Session is actively running.
    PAUSED : str
        Session is paused and can be resumed.
    COMPLETED : str
        Session has completed successfully.
    ABANDONED : str
        Session was abandoned by user.
    ERROR : str
        Session ended due to an error.
    """

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ERROR = "ERROR"


@dataclass
class SessionContext:
    """Session context holding state and metadata.

    This dataclass encapsulates all information about a session including
    its complexity assessment, state, timestamps, and flexible metadata
    storage.

    Attributes
    ----------
    session_id : str
        Unique identifier for the session.
    created_at : datetime
        When the session was created.
    updated_at : datetime
        When the session was last updated.
    complexity_score : int
        Numerical complexity score (0-100).
    complexity_level : ComplexityLevel
        Complexity level (SIMPLE, MEDIUM, COMPLEX).
    state : SessionState
        Current session state.
    metadata : dict[str, Any]
        Flexible metadata storage for session-specific data.
    messages : list[dict[str, Any]]
        Conversation messages in the session.
    task_history : list[dict[str, Any]]
        History of tasks executed in the session.

    Examples
    --------
    Create a new session context:

        ctx = SessionContext(
            session_id="sess_xyz789",
            complexity_score=55,
            complexity_level=ComplexityLevel.MEDIUM,
        )
        ctx.metadata["project"] = "my-project"

    Check complexity level:

        if ctx.complexity_level == ComplexityLevel.SIMPLE:
            print("Fast path execution")
    """

    session_id: str
    created_at: datetime
    updated_at: datetime
    complexity_score: int = 0
    complexity_level: ComplexityLevel = ComplexityLevel.SIMPLE
    state: SessionState = SessionState.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)
    task_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert session context to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the session context.
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "complexity_score": self.complexity_score,
            "complexity_level": self.complexity_level.value,
            "state": self.state.value,
            "metadata": self.metadata,
            "messages": self.messages,
            "task_history": self.task_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionContext:
        """Create session context from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing session data.

        Returns
        -------
        SessionContext
            SessionContext instance created from the dictionary.
        """
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            complexity_score=data.get("complexity_score", 0),
            complexity_level=ComplexityLevel(data.get("complexity_level", "SIMPLE")),
            state=SessionState(data.get("state", "ACTIVE")),
            metadata=data.get("metadata", {}),
            messages=data.get("messages", []),
            task_history=data.get("task_history", []),
        )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session.

        Parameters
        ----------
        role : str
            Role of the message sender (user, assistant, system).
        content : str
            Content of the message.
        """
        self.messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.updated_at = datetime.now()

    def add_task(self, task_id: str, description: str, status: str) -> None:
        """Add a task to the session history.

        Parameters
        ----------
        task_id : str
            Unique identifier for the task.
        description : str
            Description of the task.
        status : str
            Current status of the task.
        """
        self.task_history.append(
            {
                "task_id": task_id,
                "description": description,
                "status": status,
                "added_at": datetime.now().isoformat(),
            }
        )
        self.updated_at = datetime.now()

    def update_metadata(self, key: str, value: Any) -> None:
        """Update a metadata value.

        Parameters
        ----------
        key : str
            Metadata key to update.
        value : Any
            Value to set for the metadata key.
        """
        self.metadata[key] = value
        self.updated_at = datetime.now()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value.

        Parameters
        ----------
        key : str
            Metadata key to retrieve.
        default : Any, optional
            Default value if key is not found.

        Returns
        -------
        Any
            The metadata value or default if not found.
        """
        return self.metadata.get(key, default)
