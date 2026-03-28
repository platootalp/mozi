"""Anthropic model adapter for Mozi AI Coding Agent.

This module provides the AnthropicModelAdapter class that implements
the ModelAdapter interface for Anthropic's Claude API.

Environment
-----------
ANTHROPIC_API_KEY : str
    Required. The API key for Anthropic authentication.

Examples
--------
Create an Anthropic adapter:

    adapter = AnthropicModelAdapter(
        api_key="sk-ant-...",
        model="claude-sonnet-4-20250514"
    )
    response = await adapter.chat([
        ChatMessage(role="user", content="Hello!")
    ])
"""

from __future__ import annotations

import os
from typing import Any, ClassVar, cast

import anthropic
from anthropic.types import MessageParam, TextBlock

from mozi.infrastructure.model.adapter import (
    ChatMessage,
    ModelAdapter,
    ModelAdapterError,
    ModelProvider,
    ModelResponse,
)


class AnthropicModelAdapter(ModelAdapter):
    """Model adapter for Anthropic's Claude API.

    This adapter provides integration with Anthropic's Claude models
    using the official Anthropic SDK.

    Attributes
    ----------
    DEFAULT_MODEL : str
        The default model identifier for Claude.

    Examples
    --------
    Create and use the adapter:

        adapter = AnthropicModelAdapter()
        response = await adapter.chat([
            ChatMessage(role="user", content="What is 2+2?")
        ])
        print(response.content)
    """

    DEFAULT_MODEL: ClassVar[str] = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the Anthropic model adapter.

        Parameters
        ----------
        api_key : str | None, optional
            The Anthropic API key. If not provided, reads from
            ANTHROPIC_API_KEY environment variable.
        model : str | None, optional
            The model identifier. Defaults to DEFAULT_MODEL.
        base_url : str | None, optional
            The base URL for the API. If not provided, reads from
            ANTHROPIC_BASE_URL environment variable.
        max_retries : int, optional
            Maximum number of retry attempts. Default is 3.
        timeout : float, optional
            Request timeout in seconds. Default is 60.0.

        Raises
        ------
        ModelAdapterError
            If the API key is not provided and not found in environment.
        """
        resolved_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_api_key:
            raise ModelAdapterError(
                "ANTHROPIC_API_KEY environment variable is not set",
                provider=ModelProvider.ANTHROPIC,
            )

        resolved_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        resolved_model = model or self.DEFAULT_MODEL
        super().__init__(
            provider=ModelProvider.ANTHROPIC,
            api_key=resolved_api_key,
            model=resolved_model,
            max_retries=max_retries,
            timeout=timeout,
        )

        client_kwargs: dict[str, Any] = {
            "api_key": resolved_api_key,
            "timeout": self._timeout,
            "max_retries": max_retries,
        }
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url

        self._client: anthropic.AsyncAnthropic = anthropic.AsyncAnthropic(
            **client_kwargs,
        )
        self._last_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    async def complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float = 1.0,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a completion for the given prompt.

        Parameters
        ----------
        prompt : str
            The prompt to generate a completion for.
        max_tokens : int | None, optional
            Maximum number of tokens to generate.
        temperature : float, optional
            Sampling temperature. Default is 1.0.
        **kwargs : Any
            Additional Anthropic-specific parameters.

        Returns
        -------
        ModelResponse
            The model response.

        Raises
        ------
        ModelAdapterError
            If the API call fails.
        """
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or 1024,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

            text_block = cast(TextBlock, response.content[0])
            self._last_usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": (
                    response.usage.input_tokens + response.usage.output_tokens
                ),
            }
            return ModelResponse(
                content=text_block.text,
                model=response.model,
                usage=self._last_usage,
                stop_reason=response.stop_reason,
            )
        except anthropic.APIError as e:
            raise ModelAdapterError(
                f"Anthropic API error: {e}",
                provider=ModelProvider.ANTHROPIC,
                cause=e,
            ) from e
        except Exception as e:
            raise ModelAdapterError(
                f"Unexpected error during completion: {e}",
                provider=ModelProvider.ANTHROPIC,
                cause=e,
            ) from e

    async def chat(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float = 1.0,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a chat response for the given messages.

        Parameters
        ----------
        messages : list[ChatMessage]
            The conversation messages.
        max_tokens : int | None, optional
            Maximum number of tokens to generate.
        temperature : float, optional
            Sampling temperature. Default is 1.0.
        **kwargs : Any
            Additional Anthropic-specific parameters.

        Returns
        -------
        ModelResponse
            The model response.

        Raises
        ------
        ModelAdapterError
            If the API call fails.
        """
        try:
            anthropic_messages: list[MessageParam] = []
            for msg in messages:
                anthropic_messages.append({
                    "role": msg.role,  # type: ignore[typeddict-item]
                    "content": msg.content,
                })

            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or 1024,
                temperature=temperature,
                messages=anthropic_messages,
                **kwargs,
            )

            text_block = cast(TextBlock, response.content[0])
            self._last_usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": (
                    response.usage.input_tokens + response.usage.output_tokens
                ),
            }
            return ModelResponse(
                content=text_block.text,
                model=response.model,
                usage=self._last_usage,
                stop_reason=response.stop_reason,
            )
        except anthropic.APIError as e:
            raise ModelAdapterError(
                f"Anthropic API error: {e}",
                provider=ModelProvider.ANTHROPIC,
                cause=e,
            ) from e
        except Exception as e:
            raise ModelAdapterError(
                f"Unexpected error during chat: {e}",
                provider=ModelProvider.ANTHROPIC,
                cause=e,
            ) from e

    async def get_usage(self) -> dict[str, int]:
        """Get the current token usage statistics.

        Note: Anthropic API does not persist usage statistics between calls.
        This method returns the usage from the last API call only.

        Returns
        -------
        dict[str, int]
            Dictionary with prompt_tokens, completion_tokens, and total_tokens.
        """
        return self._last_usage
