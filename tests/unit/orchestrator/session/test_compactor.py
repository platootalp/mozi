"""Tests for mozi.orchestrator.session.compactor module.

This module contains unit tests for ContextCompactor and CompactionResult.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from mozi.orchestrator.session.models import SessionMessage
from mozi.orchestrator.session.compactor import CompactionResult, ContextCompactor


class TestCompactionResult:
    """Tests for CompactionResult dataclass."""

    def test_compaction_result_creation(self) -> None:
        """Test CompactionResult creation with all fields."""
        result = CompactionResult(
            original_count=100,
            compacted_count=20,
            original_tokens=10000,
            compacted_tokens=2000,
            messages=[],
        )
        assert result.original_count == 100
        assert result.compacted_count == 20
        assert result.original_tokens == 10000
        assert result.compacted_tokens == 2000
        assert result.messages == []

    def test_compaction_result_with_messages(self) -> None:
        """Test CompactionResult with actual messages."""
        now = datetime.now()
        messages = [
            SessionMessage(
                id="msg_001",
                role="user",
                content="Hello",
                timestamp=now,
                tokens=10,
            ),
        ]
        result = CompactionResult(
            original_count=10,
            compacted_count=1,
            original_tokens=1000,
            compacted_tokens=10,
            messages=messages,
        )
        assert len(result.messages) == 1
        assert result.messages[0].id == "msg_001"


class TestContextCompactor:
    """Tests for ContextCompactor class."""

    @pytest.fixture
    def compactor(self) -> ContextCompactor:
        """Create a ContextCompactor with small context limit for testing."""
        return ContextCompactor(context_limit=1000)

    def test_default_context_limit(self) -> None:
        """Test default context limit is 100000."""
        compactor = ContextCompactor()
        assert compactor.DEFAULT_CONTEXT_LIMIT == 100000

    def test_compaction_threshold(self) -> None:
        """Test compaction threshold is 0.95."""
        compactor = ContextCompactor()
        assert compactor.COMPACTION_THRESHOLD == 0.95

    def test_preserve_recent_count(self) -> None:
        """Test preserve recent count is 10."""
        compactor = ContextCompactor()
        assert compactor.PRESERVE_RECENT_COUNT == 10

    def test_should_compact_below_threshold(self) -> None:
        """Test should_compact returns False when below threshold."""
        compactor = ContextCompactor(context_limit=10000)
        now = datetime.now()
        messages = [
            SessionMessage(
                id="msg_001",
                role="user",
                content="Hello",
                timestamp=now,
                tokens=100,
            ),
        ]
        assert compactor.should_compact(messages) is False

    @pytest.mark.asyncio
    async def test_compact_preserves_recent_messages(self) -> None:
        """Test compact preserves the most recent messages."""
        compactor = ContextCompactor(context_limit=1000)
        now = datetime.now()
        # Create 25 messages to trigger compaction (1250 tokens > 950 threshold)
        # Messages 1-15 are old, messages 16-25 are recent
        messages = [
            SessionMessage(
                id=f"msg_{i:03d}",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=now - timedelta(minutes=50 - i),
                tokens=50,
            )
            for i in range(1, 26)
        ]

        result = await compactor.compact(messages)

        # Most recent messages (msg_023, msg_024, msg_025) should be preserved
        assert any(m.id == "msg_023" for m in result.messages)
        assert any(m.id == "msg_024" for m in result.messages)
        assert any(m.id == "msg_025" for m in result.messages)
        # Oldest message (msg_001) should be summarized/removed
        assert not any(m.id == "msg_001" for m in result.messages)
        # Compaction should actually reduce messages
        assert len(result.messages) < len(messages)

    @pytest.mark.asyncio
    async def test_compact_triggers_at_threshold(self) -> None:
        """Test should_compact returns True when at threshold."""
        compactor = ContextCompactor(context_limit=1000)
        now = datetime.now()
        messages = [
            SessionMessage(
                id=f"msg_{i:03d}",
                role="user",
                content=f"Message {i}",
                timestamp=now - timedelta(minutes=i),
                tokens=10,
            )
            for i in range(200)
        ]

        # Total tokens = 2000, context limit = 1000, threshold = 950
        assert compactor.should_compact(messages) is True

    @pytest.mark.asyncio
    async def test_compact_reduces_message_count(self) -> None:
        """Test compact reduces the number of messages through summarization."""
        compactor = ContextCompactor(context_limit=1000)
        now = datetime.now()
        # Create 20 messages with 50 tokens each = 1000 tokens total
        messages = [
            SessionMessage(
                id=f"msg_{i:03d}",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i} with some content",
                timestamp=now - timedelta(minutes=i),
                tokens=50,
            )
            for i in range(20)
        ]

        result = await compactor.compact(messages)

        # The compacted list should have fewer messages
        assert len(result.messages) < len(messages)
