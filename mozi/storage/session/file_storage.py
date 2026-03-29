"""File-based session storage using JSON Lines format."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mozi.orchestrator.session.models import SessionMessage


class FileSessionStorage:
    """File-based session storage using JSON Lines format.

    Storage structure: {base_path}/{session_id}/conversation.jsonl

    This class provides persistent storage for session messages using
    JSON Lines format, where each line is a valid JSON object
    representing a single message.

    Parameters
    ----------
    base_path : str
        Base directory path for storing session files.

    Examples
    --------
    Create a storage instance:

        storage = FileSessionStorage("/tmp/sessions")

    Append a message to a session:

        msg = SessionMessage(
            id="msg_001",
            role="user",
            content="Hello",
            timestamp=datetime.now(),
            tokens=5,
        )
        await storage.append_message("sess_123", msg)

    Load all messages from a session:

        messages = await storage.load_messages("sess_123")
    """

    def __init__(self, base_path: str) -> None:
        """Initialize the file storage.

        Parameters
        ----------
        base_path : str
            Base directory path for storing session files.
        """
        self._base_path = Path(base_path)

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session.

        Parameters
        ----------
        session_id : str
            Unique identifier for the session.

        Returns
        -------
        Path
            Path to the session's conversation.jsonl file.
        """
        return self._base_path / session_id / "conversation.jsonl"

    async def append_message(
        self, session_id: str, message: SessionMessage
    ) -> None:
        """Append a message to a session's conversation.

        Parameters
        ----------
        session_id : str
            Unique identifier for the session.
        message : SessionMessage
            The message to append.

        Raises
        ------
        IOError
            If the file cannot be written.
        """
        session_path = self._get_session_path(session_id)
        session_path.parent.mkdir(parents=True, exist_ok=True)

        with open(session_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message.to_dict()) + "\n")

    async def load_messages(self, session_id: str) -> list[SessionMessage]:
        """Load all messages from a session's conversation.

        Parameters
        ----------
        session_id : str
            Unique identifier for the session.

        Returns
        -------
        list[SessionMessage]
            List of messages in the session, ordered by append time.
            Returns an empty list if the session has no messages.
        """
        from mozi.orchestrator.session.models import SessionMessage

        session_path = self._get_session_path(session_id)

        if not session_path.exists():
            return []

        messages: list[SessionMessage] = []
        with open(session_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    messages.append(SessionMessage.from_dict(data))

        return messages

    async def overwrite_messages(
        self, session_id: str, messages: list[SessionMessage]
    ) -> None:
        """Overwrite a session's conversation with new messages.

        Parameters
        ----------
        session_id : str
            Unique identifier for the session.
        messages : list[SessionMessage]
            The messages to write.

        Raises
        ------
        IOError
            If the file cannot be written.
        """
        session_path = self._get_session_path(session_id)
        session_path.parent.mkdir(parents=True, exist_ok=True)

        with open(session_path, "w", encoding="utf-8") as f:
            for message in messages:
                f.write(json.dumps(message.to_dict()) + "\n")

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its data.

        Parameters
        ----------
        session_id : str
            Unique identifier for the session.
        """
        session_path = self._get_session_path(session_id)
        session_dir = session_path.parent

        if session_dir.exists():
            shutil.rmtree(session_dir)
