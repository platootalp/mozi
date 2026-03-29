"""Session data models for Mozi AI Coding Agent.

This module provides data classes and enums for session message handling.

Examples
--------
Create a session message:

    msg = SessionMessage(
        id="msg_001",
        role="user",
        content="Hello",
        timestamp=datetime.now(),
        tokens=10,
    )

Serialize to dictionary:

    data = msg.to_dict()

Deserialize from dictionary:

    msg = SessionMessage.from_dict(data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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
class SessionMessage:
    """A message in a session conversation.

    This dataclass represents a single message in a session's conversation
    history, tracking the role, content, tokens, and any artifacts associated
    with the message.

    Attributes
    ----------
    id : str
        Unique identifier for the message.
    role : str
        Role of the message sender (user, assistant, system).
    content : str
        Content of the message.
    timestamp : datetime
        When the message was created.
    tokens : int
        Number of tokens in the message.
    artifacts : list[Any]
        Associated artifacts (e.g., code, files).

    Examples
    --------
    Create a user message:

        msg = SessionMessage(
            id="msg_123",
            role="user",
            content="Implement login feature",
            timestamp=datetime.now(),
            tokens=8,
        )

    Create an assistant message with artifacts:

        msg = SessionMessage(
            id="msg_456",
            role="assistant",
            content="Here is the implementation",
            timestamp=datetime.now(),
            tokens=150,
            artifacts=[{"type": "code", "content": "def login(): pass"}],
        )
    """

    id: str
    role: str
    content: str
    timestamp: datetime
    tokens: int = 0
    artifacts: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert session message to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the session message.
        """
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tokens": self.tokens,
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionMessage:
        """Create session message from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing message data.

        Returns
        -------
        SessionMessage
            SessionMessage instance created from the dictionary.
        """
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens=data.get("tokens", 0),
            artifacts=data.get("artifacts", []),
        )
