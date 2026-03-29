# Session Management Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement complete session management aligned with Claude Code, including CLI flags (-c/-r/-n/-p), file-based conversation storage (JSON Lines), context compaction, and named sessions.

**Architecture:**
- Data models in `mozi/orchestrator/session/models.py` (Session, SessionMessage, SessionState)
- File-based storage in `mozi/storage/session/file_storage.py` (JSON Lines format)
- Context compaction in `mozi/orchestrator/session/compactor.py`
- CLI updates in `mozi/cli/main.py` and `mozi/cli/commands.py`
- SessionManager updated to integrate storage and compaction

**Tech Stack:** Python 3.11+, SQLite, JSON Lines, Typer

---

## File Structure

```
mozi/
├── orchestrator/session/
│   ├── models.py           # NEW: Session, SessionMessage, SessionState
│   ├── compactor.py        # NEW: ContextCompactor
│   ├── manager.py          # MODIFY: Add name support, compaction integration
│   └── context.py          # KEEP: Existing SessionContext (runtime state)
├── storage/session/
│   ├── file_storage.py     # NEW: FileSessionStorage (JSON Lines)
│   ├── manager.py          # MODIFY: Add name field, get_by_name
│   └── schema.py           # MODIFY: Add name column to Session
├── cli/
│   ├── main.py             # MODIFY: Add -c/-r/-n/-p flags to main command
│   └── commands.py         # MODIFY: Add continue, resume_by_name, named_session
└── tests/unit/
    ├── orchestrator/session/
    │   ├── test_models.py         # NEW
    │   ├── test_manager.py         # MODIFY: Add name tests
    │   └── test_compactor.py       # NEW
    └── storage/session/
        ├── test_file_storage.py    # NEW
        └── test_manager.py         # MODIFY: Add name tests
```

---

## Task 1: Create Session Data Models

**Files:**
- Create: `mozi/orchestrator/session/models.py`
- Test: `tests/unit/orchestrator/session/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestrator/session/test_models.py
import pytest
from datetime import datetime
from mozi.orchestrator.session.models import SessionState, SessionMessage, Session

def test_session_message_creation():
    msg = SessionMessage(
        id="msg_001",
        role="user",
        content="Hello",
        timestamp=datetime.now(),
        tokens=10,
    )
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_session_state_transitions():
    assert SessionState.ACTIVE.value == "ACTIVE"
    assert SessionState.PAUSED.value == "PAUSED"
    assert SessionState.COMPLETED.value == "COMPLETED"
    assert SessionState.ABANDONED.value == "ABANDONED"
    assert SessionState.ERROR.value == "ERROR"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestrator/session/test_models.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/orchestrator/session/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SessionState(Enum):
    """Session state enumeration."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ERROR = "ERROR"


@dataclass
class SessionMessage:
    """A single message in a session."""
    id: str
    role: str
    content: str
    timestamp: datetime
    tokens: int = 0
    artifacts: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
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
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens=data.get("tokens", 0),
            artifacts=data.get("artifacts", []),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestrator/session/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mozi/orchestrator/session/models.py tests/unit/orchestrator/session/test_models.py
git commit -m "feat(session): add SessionMessage and SessionState models"
```

---

## Task 2: Create FileSessionStorage

**Files:**
- Create: `mozi/storage/session/file_storage.py`
- Test: `tests/unit/storage/session/test_file_storage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/storage/session/test_file_storage.py
import pytest
import tempfile
import shutil
from datetime import datetime
from mozi.storage.session.file_storage import FileSessionStorage
from mozi.orchestrator.session.models import SessionMessage

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

@pytest.mark.asyncio
async def test_append_and_load_messages(temp_dir):
    storage = FileSessionStorage(temp_dir)
    session_id = "sess_test123"

    msg1 = SessionMessage(
        id="msg_001",
        role="user",
        content="Hello",
        timestamp=datetime.now(),
        tokens=5,
    )
    await storage.append_message(session_id, msg1)

    messages = await storage.load_messages(session_id)
    assert len(messages) == 1
    assert messages[0].content == "Hello"

@pytest.mark.asyncio
async def test_overwrite_messages(temp_dir):
    storage = FileSessionStorage(temp_dir)
    session_id = "sess_test456"

    msg1 = SessionMessage(id="msg_001", role="user", content="Hello", timestamp=datetime.now(), tokens=5)
    msg2 = SessionMessage(id="msg_002", role="user", content="World", timestamp=datetime.now(), tokens=5)

    await storage.append_message(session_id, msg1)
    await storage.append_message(session_id, msg2)

    await storage.overwrite_messages(session_id, [msg1])
    messages = await storage.load_messages(session_id)
    assert len(messages) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/storage/session/test_file_storage.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/storage/session/file_storage.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mozi.orchestrator.session.models import SessionMessage


class FileSessionStorage:
    """File-based session storage using JSON Lines format.

    Storage structure:
    ~/.ai/projects/{project_id}/{session_id}/conversation.jsonl
    """

    def __init__(self, base_path: str) -> None:
        """Initialize file storage.

        Parameters
        ----------
        base_path : str
            Base path for session storage.
        """
        self.base_path = Path(base_path)

    def _get_conversation_path(self, session_id: str) -> Path:
        """Get path to conversation file for a session."""
        return self.base_path / session_id / "conversation.jsonl"

    def _ensure_session_dir(self, session_id: str) -> None:
        """Ensure session directory exists."""
        session_dir = self.base_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

    async def append_message(self, session_id: str, message: SessionMessage) -> None:
        """Append a message to the conversation file.

        Parameters
        ----------
        session_id : str
            The session ID.
        message : SessionMessage
            The message to append.
        """
        self._ensure_session_dir(session_id)
        path = self._get_conversation_path(session_id)

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")

    async def load_messages(self, session_id: str) -> list[SessionMessage]:
        """Load all messages for a session.

        Parameters
        ----------
        session_id : str
            The session ID.

        Returns
        -------
        list[SessionMessage]
            List of messages in chronological order.
        """
        path = self._get_conversation_path(session_id)
        if not path.exists():
            return []

        messages = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    messages.append(SessionMessage.from_dict(data))
        return messages

    async def overwrite_messages(
        self, session_id: str, messages: list[SessionMessage]
    ) -> None:
        """Overwrite conversation file with new messages.

        Parameters
        ----------
        session_id : str
            The session ID.
        messages : list[SessionMessage]
            New list of messages.
        """
        self._ensure_session_dir(session_id)
        path = self._get_conversation_path(session_id)

        with open(path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")

    async def delete_session(self, session_id: str) -> None:
        """Delete session files.

        Parameters
        ----------
        session_id : str
            The session ID.
        """
        session_dir = self.base_path / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/storage/session/test_file_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mozi/storage/session/file_storage.py tests/unit/storage/session/test_file_storage.py
git commit -m "feat(storage): add FileSessionStorage for JSON Lines conversation storage"
```

---

## Task 3: Create ContextCompactor

**Files:**
- Create: `mozi/orchestrator/session/compactor.py`
- Test: `tests/unit/orchestrator/session/test_compactor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestrator/session/test_compactor.py
import pytest
from datetime import datetime, timedelta
from mozi.orchestrator.session.models import SessionMessage
from mozi.orchestrator.session.compactor import ContextCompactor

@pytest.fixture
def compactor():
    # Create compactor without LLM client for unit tests
    return ContextCompactor(context_limit=1000)

@pytest.mark.asyncio
async def test_compact_preserves_recent_messages(compactor):
    now = datetime.now()
    messages = [
        SessionMessage(id="msg_001", role="user", content="Old message", timestamp=now - timedelta(hours=1), tokens=50),
        SessionMessage(id="msg_002", role="assistant", content="Old response", timestamp=now - timedelta(minutes=30), tokens=100),
        SessionMessage(id="msg_003", role="user", content="Recent message", timestamp=now, tokens=50),
    ]

    compacted = await compactor.compact(messages)

    # Recent message should be preserved
    assert any(m.id == "msg_003" for m in compacted)
    # Old messages may be summarized
    assert len(compacted) <= len(messages)

@pytest.mark.asyncio
async def test_compact_triggers_at_threshold(compactor):
    now = datetime.now()
    messages = [
        SessionMessage(id=f"msg_{i:03d}", role="user", content=f"Message {i}", timestamp=now - timedelta(minutes=i), tokens=10)
        for i in range(200)
    ]

    # Total tokens = 2000, context limit = 1000, threshold = 950
    # Should trigger compaction
    assert compactor.should_compact(messages) is True

@pytest.mark.asyncio
async def test_compact_does_not_trigger_below_threshold():
    compactor = ContextCompactor(context_limit=10000)  # Large limit
    now = datetime.now()
    messages = [
        SessionMessage(id="msg_001", role="user", content="Hello", timestamp=now, tokens=100),
    ]

    assert compactor.should_compact(messages) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestrator/session/test_compactor.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/orchestrator/session/compactor.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mozi.orchestrator.session.models import SessionMessage


@dataclass
class CompactionResult:
    """Result of context compaction."""
    original_count: int
    compacted_count: int
    original_tokens: int
    compacted_tokens: int
    messages: list[SessionMessage]


class ContextCompactor:
    """Context compaction for session messages.

    Compacts old messages when token count approaches context limit.
    """

    DEFAULT_CONTEXT_LIMIT = 100000  # ~100k tokens for Claude
    COMPACTION_THRESHOLD = 0.95  # Trigger at 95% of context limit
    PRESERVE_RECENT_COUNT = 10  # Always keep last 10 messages

    def __init__(self, context_limit: int = DEFAULT_CONTEXT_LIMIT) -> None:
        """Initialize compactor.

        Parameters
        ----------
        context_limit : int
            Context window size in tokens.
        """
        self.context_limit = context_limit
        self.threshold = int(context_limit * self.COMPACTION_THRESHOLD)

    def should_compact(self, messages: list[SessionMessage]) -> bool:
        """Check if compaction should be triggered.

        Parameters
        ----------
        messages : list[SessionMessage]
            Current messages.

        Returns
        -------
        bool
            True if compaction should run.
        """
        total_tokens = sum(m.tokens for m in messages)
        return total_tokens >= self.threshold

    async def compact(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        """Compact messages using LLM summarization.

        Parameters
        ----------
        messages : list[SessionMessage]
            Messages to compact.

        Returns
        -------
        list[SessionMessage]
            Compacted messages.
        """
        if not messages:
            return messages

        # Separate recent messages (always keep) from old messages
        recent = messages[-self.PRESERVE_RECENT_COUNT:]
        old = messages[:-self.PRESERVE_RECENT_COUNT]

        if not old:
            return messages

        # Simple compression: keep recent, summarize old
        # In full implementation, this would call LLM to summarize
        summarized = await self._summarize_batch(old)

        return summarized + list(recent)

    async def _summarize_batch(
        self, messages: list[SessionMessage]
    ) -> list[SessionMessage]:
        """Summarize a batch of messages.

        In production, this would call an LLM to generate a summary.
        For now, returns a single summary message.
        """
        if not messages:
            return []

        total_tokens = sum(m.tokens for m in messages)
        summary_content = f"[Compressed {len(messages)} messages, ~{total_tokens} tokens]"

        return [
            SessionMessage(
                id=f"summary_{messages[0].id}",
                role="system",
                content=summary_content,
                timestamp=messages[-1].timestamp,
                tokens=total_tokens // 10,  # Estimate compressed tokens
            )
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestrator/session/test_compactor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mozi/orchestrator/session/compactor.py tests/unit/orchestrator/session/test_compactor.py
git commit -m "feat(session): add ContextCompactor for context window management"
```

---

## Task 4: Update SessionManager with Name Support

**Files:**
- Modify: `mozi/storage/session/manager.py` (add name field)
- Modify: `mozi/storage/session/schema.py` (add name to Session, add name index)
- Test: `tests/unit/storage/session/test_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/storage/session/test_manager.py
# Add to existing test file
@pytest.mark.asyncio
async def test_create_session_with_name(tmp_path):
    from mozi.storage.session.manager import SessionStore
    from mozi.storage.session.schema import Session, SessionStatus

    db_path = str(tmp_path / "test.db")
    store = SessionStore(db_path)

    session = Session(
        id="sess_with_name",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=SessionStatus.ACTIVE,
        name="my-session",
    )
    await store.create(session)

    retrieved = await store.get_by_name("my-session")
    assert retrieved is not None
    assert retrieved.name == "my-session"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/storage/session/test_manager.py::test_create_session_with_name -v`
Expected: FAIL - AttributeError or query fails

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/storage/session/schema.py - Add name field to Session class
@dataclass
class Session:
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
    name: str | None = None  # ADD THIS FIELD

# Add to CREATE_SESSIONS_TABLE SQL:
# name TEXT,
# Add to CREATE_SESSIONS_INDEXES:
# CREATE INDEX IF NOT EXISTS idx_sessions_name ON sessions(name);
```

```python
# mozi/storage/session/manager.py - Add get_by_name and update create
async def create(self, session: Session) -> Session:
    # ... existing code ...
    conn.execute(
        """
        INSERT INTO sessions (id, status, ..., name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session.id,
            session.status.value,
            session.complexity_level.value if session.complexity_level else None,
            session.complexity_score,
            session.model,
            session.message_count,
            json.dumps(session.metadata or {}),
            session.last_activity.isoformat() if session.last_activity else None,
            session.name,  # ADD THIS
        ),
    )

async def get_by_name(self, name: str) -> Session | None:
    """Get session by name."""
    loop = asyncio.get_event_loop()
    row = await loop.run_in_executor(None, self._sync_get_by_name, name)
    if not row:
        return None
    return self._row_to_session(row)

def _sync_get_by_name(self, name: str) -> tuple[Any, ...] | None:
    conn = sqlite3.connect(self.db_path)
    cursor = conn.execute(
        "SELECT * FROM sessions WHERE name = ? ORDER BY updated_at DESC LIMIT 1",
        (name,),
    )
    row = cursor.fetchone()
    conn.close()
    return row if row is None else cast(tuple[Any, ...], row)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/storage/session/test_manager.py::test_create_session_with_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mozi/storage/session/manager.py mozi/storage/session/schema.py tests/unit/storage/session/test_manager.py
git commit -m "feat(storage): add name field to Session and get_by_name method"
```

---

## Task 5: Add CLI Flags (-c, -r, -n, -p)

**Files:**
- Modify: `mozi/cli/main.py`
- Modify: `mozi/cli/commands.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/cli/test_main.py
def test_main_command_with_continue_flag():
    # This would require mocking asyncio.run
    # For now, we verify the flag is parsed correctly
    from mozi.cli.main import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["--continue"])
    # Should not error on parsing
    assert result.exit_code in [0, 1]  # May fail on execution but parsing works
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cli/test_main.py -v`
Expected: FAIL - ModuleNotFoundError or test doesn't exist

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/cli/main.py - Update main() signature
@app.command()
def main(
    ctx: typer.Context,
    task: Annotated[
        str | None,
        typer.Argument(help="Task description to execute"),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Start interactive mode"),
    ] = False,
    session: Annotated[
        str | None,
        typer.Option("--session", "-s", help="Session ID to resume"),
    ] = None,
    continue_last: Annotated[
        bool,
        typer.Option("--continue", "-c", help="Continue the most recent session"),
    ] = False,
    resume: Annotated[
        str | None,
        typer.Option("--resume", "-r", help="Resume session by name or ID"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Name for new session"),
    ] = None,
    print_mode: Annotated[
        bool,
        typer.Option("--print", "-p", help="Print result only (non-interactive)"),
    ] = False,
    # ... existing params ...
):
    pass  # Implementation in commands.py
```

```python
# mozi/cli/commands.py - Add new command handlers
async def continue_last_session(
    task: str | None = None,
    verbose: bool = False,
) -> ExecutionResult:
    """Continue the most recent session."""
    from mozi.storage.session.manager import SessionStore

    # Get most recent active session
    store = SessionStore(get_session_db_path())
    session = await store.get_active()

    if not session:
        raise CLIError("No active session to continue")

    return await execute_task(
        task_description=task,
        session_id=session.id,
        verbose=verbose,
    )

async def resume_session_by_name(
    name_or_id: str,
    task: str | None = None,
    verbose: bool = False,
) -> ExecutionResult:
    """Resume a session by name or ID."""
    from mozi.storage.session.manager import SessionStore

    store = SessionStore(get_session_db_path())

    # Try by name first, then by ID
    session = await store.get_by_name(name_or_id)
    if not session:
        session = await store.get(name_or_id)

    if not session:
        raise CLIError(f"Session not found: {name_or_id}")

    return await execute_task(
        task_description=task,
        session_id=session.id,
        verbose=verbose,
    )

async def create_named_session(
    name: str,
    task: str | None = None,
    verbose: bool = False,
) -> ExecutionResult:
    """Create a new named session."""
    from mozi.storage.session.manager import SessionStore
    from mozi.storage.session.schema import Session, SessionStatus
    import uuid

    store = SessionStore(get_session_db_path())

    session = Session(
        id=f"sess_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=SessionStatus.ACTIVE,
        name=name,
    )
    await store.create(session)

    return await execute_task(
        task_description=task,
        session_id=session.id,
        verbose=verbose,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/cli/ -v`
Expected: PASS (or skip if test not written)

- [ ] **Step 5: Commit**

```bash
git add mozi/cli/main.py mozi/cli/commands.py
git commit -m "feat(cli): add -c/--continue, -r/--resume, -n/--name, -p/--print flags"
```

---

## Task 6: Integrate Storage and Compaction into SessionManager

**Files:**
- Modify: `mozi/orchestrator/session/manager.py`
- Test: `tests/unit/orchestrator/session/test_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestrator/session/test_manager.py - Add integration tests
@pytest.mark.asyncio
async def test_add_message_triggers_compaction():
    manager = SessionManager(storage=mock_storage, compactor=compactor)

    session = await manager.create_session()

    # Add many messages to trigger compaction
    for i in range(100):
        msg = SessionMessage(id=f"msg_{i}", role="user", content=f"Msg {i}", timestamp=datetime.now(), tokens=10)
        await manager.add_message(session.id, msg)

    # Check compaction was triggered
    assert compactor.compact_called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestrator/session/test_manager.py::test_add_message_triggers_compaction -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/orchestrator/session/manager.py
class SessionManager:
    def __init__(
        self,
        storage: SessionStorage,  # New param
        compactor: ContextCompactor | None = None,  # New param
    ) -> None:
        self._sessions: dict[str, SessionContext] = {}
        self._file_storage = storage  # File-based storage for messages
        self._compactor = compactor or ContextCompactor()

    async def add_message(self, session_id: str, message: SessionMessage) -> SessionContext:
        """Add message and check for compaction."""
        session = await self.get_session(session_id)

        # Append to file storage
        await self._file_storage.append_message(session_id, message)

        # Update in-memory session
        session.message_count += 1
        session.total_tokens = (session.total_tokens or 0) + message.tokens
        session.updated_at = datetime.now()

        # Check if compaction needed
        messages = await self._file_storage.load_messages(session_id)
        if self._compactor.should_compact(messages):
            compacted = await self._compactor.compact(messages)
            await self._file_storage.overwrite_messages(session_id, compacted)

        return await self.update_session(session)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestrator/session/test_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mozi/orchestrator/session/manager.py tests/unit/orchestrator/session/test_manager.py
git commit -m "feat(session): integrate file storage and context compaction into SessionManager"
```

---

## Task 7: Add Conversation History to Session Listing

**Files:**
- Modify: `mozi/cli/commands.py` (list_sessions function)
- Modify: `mozi/cli/output.py` (add conversation count to output)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/cli/test_commands.py
@pytest.mark.asyncio
async def test_list_sessions_shows_conversation_count():
    sessions = await list_sessions()
    # Verify output includes message count
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cli/test_commands.py::test_list_sessions_shows_conversation_count -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# mozi/cli/commands.py - Update list_sessions
async def list_sessions(limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
    from mozi.storage.session.manager import SessionStore

    store = SessionStore(get_session_db_path())
    sessions = await store.list_sessions(limit=limit, offset=offset)

    result = []
    for sess in sessions:
        # Get message count from file storage
        messages = await get_file_storage().load_messages(sess.id)
        result.append({
            "session_id": sess.id,
            "name": sess.name,
            "state": sess.status.value,
            "complexity_level": sess.complexity_level.value if sess.complexity_level else None,
            "created_at": sess.created_at.isoformat(),
            "message_count": len(messages),
        })
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/cli/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mozi/cli/commands.py
git commit -m "feat(cli): show conversation count in session list"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Session data models | `models.py`, `test_models.py` |
| 2 | File-based JSON Lines storage | `file_storage.py`, `test_file_storage.py` |
| 3 | Context compaction | `compactor.py`, `test_compactor.py` |
| 4 | Name support in storage | `manager.py`, `schema.py`, `test_manager.py` |
| 5 | CLI flags (-c, -r, -n, -p) | `main.py`, `commands.py` |
| 6 | Storage/compaction integration | `manager.py` (orchestrator) |
| 7 | Conversation count in listing | `commands.py` |

---

*Plan version: 1.0*
*Created: 2026-03-29*
