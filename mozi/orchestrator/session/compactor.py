"""Context compaction for session message management.

This module provides context window management through message summarization
to keep conversation history within model context limits.

Examples
--------
Create a compactor and check if compaction is needed:

    compactor = ContextCompactor(context_limit=100000)
    if compactor.should_compact(messages):
        messages = await compactor.compact(messages)

Get compaction statistics:

    result = await compactor.compact(messages)
    print(f"Reduced from {result.original_count} to {result.compacted_count} messages")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mozi.orchestrator.session.models import SessionMessage


@dataclass
class CompactionResult:
    """Result of a context compaction operation.

    Attributes
    ----------
    original_count : int
        Number of messages before compaction.
    compacted_count : int
        Number of messages after compaction.
    original_tokens : int
        Total tokens before compaction.
    compacted_tokens : int
        Total tokens after compaction.
    messages : list[SessionMessage]
        The compacted message list.
    """

    original_count: int
    compacted_count: int
    original_tokens: int
    compacted_tokens: int
    messages: list[SessionMessage]


class ContextCompactor:
    """Manages context window through message summarization.

    This class handles context window management by triggering compaction
    when the context approaches its limit, and performing summarization
    on older messages to preserve recent context.

    Attributes
    ----------
    DEFAULT_CONTEXT_LIMIT : int
        Default context limit of approximately 100k tokens for Claude.
    COMPACTION_THRESHOLD : float
        Trigger compaction at 95% of context limit.
    PRESERVE_RECENT_COUNT : int
        Always keep the last 10 messages unsummarized.

    Examples
    --------
    Check if compaction is needed:

        compactor = ContextCompactor()
        if compactor.should_compact(messages):
            messages = await compactor.compact(messages)

    Compact with custom limit:

        compactor = ContextCompactor(context_limit=50000)
        compacted = await compactor.compact(messages)
    """

    DEFAULT_CONTEXT_LIMIT: int = 100000
    COMPACTION_THRESHOLD: float = 0.95
    PRESERVE_RECENT_COUNT: int = 10

    def __init__(self, context_limit: int = DEFAULT_CONTEXT_LIMIT) -> None:
        """Initialize the ContextCompactor.

        Parameters
        ----------
        context_limit : int, optional
            Maximum tokens in context window, by default DEFAULT_CONTEXT_LIMIT.
        """
        self._context_limit = context_limit

    @property
    def context_limit(self) -> int:
        """Get the context limit.

        Returns
        -------
        int
            Maximum tokens in context window.
        """
        return self._context_limit

    @property
    def compaction_threshold_tokens(self) -> int:
        """Get the token count that triggers compaction.

        Returns
        -------
        int
            Token count at which compaction is triggered.
        """
        return int(self._context_limit * self.COMPACTION_THRESHOLD)

    def should_compact(self, messages: list[SessionMessage]) -> bool:
        """Determine if compaction should be triggered.

        Compaction is triggered when total tokens exceed 95% of context limit.

        Parameters
        ----------
        messages : list[SessionMessage]
            List of session messages to check.

        Returns
        -------
        bool
            True if compaction should be triggered, False otherwise.
        """
        total_tokens = sum(msg.tokens for msg in messages)
        return total_tokens > self.compaction_threshold_tokens

    async def compact(self, messages: list[SessionMessage]) -> CompactionResult:
        """Compact messages by summarizing older ones.

        This method preserves the most recent messages (PRESERVE_RECENT_COUNT)
        and summarizes older messages into a compact form.

        Parameters
        ----------
        messages : list[SessionMessage]
            List of session messages to compact.

        Returns
        -------
        CompactionResult
            Compaction result containing original and compacted statistics
            along with the compacted message list.
        """
        original_count = len(messages)
        original_tokens = sum(msg.tokens for msg in messages)

        if len(messages) <= self.PRESERVE_RECENT_COUNT:
            compacted_messages = list(messages)
            return CompactionResult(
                original_count=original_count,
                compacted_count=len(compacted_messages),
                original_tokens=original_tokens,
                compacted_tokens=sum(msg.tokens for msg in compacted_messages),
                messages=compacted_messages,
            )

        preserved = messages[-self.PRESERVE_RECENT_COUNT :]
        to_summarize = messages[: -self.PRESERVE_RECENT_COUNT]

        summarized = await self._summarize_batch(to_summarize)
        compacted_messages = summarized + preserved

        return CompactionResult(
            original_count=original_count,
            compacted_count=len(compacted_messages),
            original_tokens=original_tokens,
            compacted_tokens=sum(msg.tokens for msg in compacted_messages),
            messages=compacted_messages,
        )

    async def _summarize_batch(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        """Summarize a batch of older messages.

        This method combines multiple messages into fewer summarized messages.
        In a production implementation, this would call an LLM API.

        Parameters
        ----------
        messages : list[SessionMessage]
            Messages to summarize.

        Returns
        -------
        list[SessionMessage]
            Summarized messages.
        """
        if not messages:
            return []

        # Group messages by role and create summary content
        role_contents: dict[str, list[str]] = {}
        total_tokens = 0
        earliest_timestamp = datetime.now()

        for msg in messages:
            if msg.role not in role_contents:
                role_contents[msg.role] = []
            role_contents[msg.role].append(msg.content)
            total_tokens += msg.tokens
            if msg.timestamp < earliest_timestamp:
                earliest_timestamp = msg.timestamp

        # Create summarized messages
        summarized_messages: list[SessionMessage] = []
        summary_id_prefix = "summary_"

        for role, contents in role_contents.items():
            combined_content = f"[Summary of {len(contents)} {role} messages]: " + " | ".join(
                contents[:3]
            )
            if len(contents) > 3:
                combined_content += f" ... and {len(contents) - 3} more messages"

            # Estimate tokens for summary (rough approximation)
            estimated_tokens = max(50, total_tokens // len(role_contents))

            summarized_messages.append(
                SessionMessage(
                    id=f"{summary_id_prefix}{role}_{messages[0].id}",
                    role=role,
                    content=combined_content,
                    timestamp=earliest_timestamp,
                    tokens=estimated_tokens,
                )
            )

        return summarized_messages
