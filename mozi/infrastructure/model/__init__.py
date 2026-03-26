"""Infrastructure layer - Model adapters.

This package provides model adapters that implement a unified interface
for interacting with different LLM providers.

Examples
--------
Create an Anthropic adapter:

    from mozi.infrastructure.model import AnthropicModelAdapter

    adapter = AnthropicModelAdapter()
    response = await adapter.chat([
        ChatMessage(role="user", content="Hello!")
    ])
"""

from __future__ import annotations

from mozi.infrastructure.model.adapter import (
    ChatMessage,
    ModelAdapter,
    ModelAdapterError,
    ModelProvider,
    ModelResponse,
)
from mozi.infrastructure.model.anthropic import AnthropicModelAdapter

__all__ = [
    "AnthropicModelAdapter",
    "ChatMessage",
    "ModelAdapter",
    "ModelAdapterError",
    "ModelProvider",
    "ModelResponse",
]
