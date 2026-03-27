"""Model adapter base class for Mozi AI Coding Agent.

This module defines the abstract base class for model adapters that provide
a unified interface for interacting with different LLM providers.

Examples
--------
Implement a custom model adapter:

    class MyModelAdapter(ModelAdapter):
        async def complete(self, prompt: str) -> str:
            # Implementation
            return response

        async def chat(self, messages: list[ChatMessage]) -> ChatMessage:
            # Implementation
            return response
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from mozi.core import MoziError


class ModelProvider(Enum):
    """Supported model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass
class ChatMessage:
    """Represents a chat message.

    Attributes
    ----------
    role : str
        The role of the message sender (user, assistant, system).
    content : str
        The content of the message.
    name : str | None
        Optional name for the message sender.
    """

    role: str
    content: str
    name: str | None = None


@dataclass
class ModelResponse:
    """Represents a response from a model.

    Attributes
    ----------
    content : str
        The text content of the response.
    model : str
        The model that generated the response.
    usage : dict[str, int]
        Token usage information.
    stop_reason : str | None
        The reason the model stopped generating.
    """

    content: str
    model: str
    usage: dict[str, int]
    stop_reason: str | None = None


class ModelAdapterError(MoziError):
    """Exception raised for model adapter errors.

    This exception is raised when there are issues with model
    API calls, authentication, or response parsing.

    Attributes
    ----------
    provider : ModelProvider | None
        The model provider involved in the error, if known.
    """

    def __init__(
        self,
        message: str,
        provider: ModelProvider | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize ModelAdapterError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        provider : ModelProvider | None, optional
            The model provider involved in the error.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.provider: ModelProvider | None = provider

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        cause_repr = repr(self.cause) if self.cause else None
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"provider={self.provider!r}, "
            f"cause={cause_repr})"
        )


class ModelAdapter(ABC):
    """Abstract base class for model adapters.

    This class defines the interface that all model adapters must implement.
    It provides methods for text completion and chat-based interactions.

    Subclasses must implement the async methods: complete, chat, and get_usage.

    Examples
    --------
    Create a custom adapter:

        class MyAdapter(ModelAdapter):
            def __init__(self, api_key: str) -> None:
                super().__init__(ModelProvider.OPENAI, api_key)

            async def complete(self, prompt: str) -> ModelResponse:
                # Call API and return response
                return ModelResponse(...)

            async def chat(self, messages: list[ChatMessage]) -> ModelResponse:
                # Call API and return response
                return ModelResponse(...)

            async def get_usage(self) -> dict[str, int]:
                return {"prompt_tokens": 0, "completion_tokens": 0}
    """

    def __init__(
        self,
        provider: ModelProvider,
        api_key: str,
        model: str,
        max_retries: int = 3,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the model adapter.

        Parameters
        ----------
        provider : ModelProvider
            The model provider type.
        api_key : str
            The API key for authentication.
        model : str
            The model identifier to use.
        max_retries : int, optional
            Maximum number of retry attempts on failure. Default is 3.
        timeout : float, optional
            Request timeout in seconds. Default is 60.0.
        """
        self._provider: ModelProvider = provider
        self._api_key: str = api_key
        self._model: str = model
        self._max_retries: int = max_retries
        self._timeout: float = timeout

    @property
    def provider(self) -> ModelProvider:
        """Get the model provider.

        Returns
        -------
        ModelProvider
            The model provider type.
        """
        return self._provider

    @property
    def model(self) -> str:
        """Get the model identifier.

        Returns
        -------
        str
            The model identifier.
        """
        return self._model

    @property
    def max_retries(self) -> int:
        """Get the maximum retry attempts.

        Returns
        -------
        int
            Maximum retry attempts.
        """
        return self._max_retries

    @property
    def timeout(self) -> float:
        """Get the request timeout.

        Returns
        -------
        float
            Request timeout in seconds.
        """
        return self._timeout

    @abstractmethod
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
            Additional provider-specific parameters.

        Returns
        -------
        ModelResponse
            The model response.

        Raises
        ------
        ModelAdapterError
            If the API call fails.
        """

    @abstractmethod
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
            Additional provider-specific parameters.

        Returns
        -------
        ModelResponse
            The model response.

        Raises
        ------
        ModelAdapterError
            If the API call fails.
        """

    @abstractmethod
    async def get_usage(self) -> dict[str, int]:
        """Get the current token usage statistics.

        Returns
        -------
        dict[str, int]
            Dictionary with prompt_tokens, completion_tokens, and total_tokens.
        """
