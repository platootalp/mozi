"""Tests for Anthropic model adapter.

These tests verify the AnthropicModelAdapter class functionality
using mocked Anthropic API responses.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.infrastructure.model import (
    AnthropicModelAdapter,
    ChatMessage,
    ModelAdapterError,
    ModelProvider,
    ModelResponse,
)


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Create a mock Anthropic client."""
    return MagicMock()


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock Anthropic message response."""
    response = MagicMock()
    response.content = [MagicMock(text="Hello! How can I help you?")]
    response.model = "claude-sonnet-4-20250514"
    response.usage = MagicMock(input_tokens=10, output_tokens=20)
    response.stop_reason = "end_turn"
    return response


@pytest.fixture
def api_key() -> str:
    """Return a test API key."""
    return "sk-ant-test-api-key"


class TestAnthropicModelAdapter:
    """Test suite for AnthropicModelAdapter class."""

    @pytest.mark.unit
    def test_init_with_api_key(self, api_key: str) -> None:
        """Test initialization with explicit API key."""
        adapter = AnthropicModelAdapter(api_key=api_key, model="test-model")

        assert adapter.provider == ModelProvider.ANTHROPIC
        assert adapter.model == "test-model"
        assert adapter.max_retries == 3
        assert adapter.timeout == 60.0

    @pytest.mark.unit
    def test_init_with_env_var(self, api_key: str) -> None:
        """Test initialization with environment variable."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": api_key}):
            adapter = AnthropicModelAdapter()

        assert adapter.provider == ModelProvider.ANTHROPIC

    @pytest.mark.unit
    def test_init_without_api_key(self) -> None:
        """Test initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ModelAdapterError) as exc_info:
                AnthropicModelAdapter()

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)
        assert exc_info.value.provider == ModelProvider.ANTHROPIC

    @pytest.mark.unit
    def test_init_with_default_model(self, api_key: str) -> None:
        """Test initialization uses default model."""
        adapter = AnthropicModelAdapter(api_key=api_key)

        assert adapter.model == AnthropicModelAdapter.DEFAULT_MODEL

    @pytest.mark.unit
    def test_init_with_custom_params(self, api_key: str) -> None:
        """Test initialization with custom parameters."""
        adapter = AnthropicModelAdapter(
            api_key=api_key,
            model="claude-opus-4-20250514",
            max_retries=5,
            timeout=120.0,
        )

        assert adapter.max_retries == 5
        assert adapter.timeout == 120.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_complete_success(
        self,
        api_key: str,
        mock_response: MagicMock,
    ) -> None:
        """Test successful completion request."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)
            response = await adapter.complete("Hello", max_tokens=100)

            assert isinstance(response, ModelResponse)
            assert response.content == "Hello! How can I help you?"
            assert response.model == "claude-sonnet-4-20250514"
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 20
            assert response.usage["total_tokens"] == 30
            assert response.stop_reason == "end_turn"

            mock_client.messages.create.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_success(
        self,
        api_key: str,
        mock_response: MagicMock,
    ) -> None:
        """Test successful chat request."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)
            messages = [
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi there!"),
            ]
            response = await adapter.chat(messages)

            assert isinstance(response, ModelResponse)
            assert response.content == "Hello! How can I help you?"

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert len(call_kwargs["messages"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_complete_with_custom_params(
        self,
        api_key: str,
        mock_response: MagicMock,
    ) -> None:
        """Test completion with custom parameters."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)
            await adapter.complete(
                "Hello",
                max_tokens=500,
                temperature=0.7,
                top_p=0.9,
            )

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["max_tokens"] == 500
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["top_p"] == 0.9

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_complete_api_error(
        self,
        api_key: str,
    ) -> None:
        """Test completion handles API errors."""
        import anthropic

        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            api_error = anthropic.APIError(
                message="API error occurred",
                request=MagicMock(),
                body=None,
            )
            mock_client.messages.create = AsyncMock(side_effect=api_error)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)

            with pytest.raises(ModelAdapterError) as exc_info:
                await adapter.complete("Hello")

            assert "API error occurred" in str(exc_info.value)
            assert exc_info.value.provider == ModelProvider.ANTHROPIC
            assert exc_info.value.cause is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_api_error(
        self,
        api_key: str,
    ) -> None:
        """Test chat handles API errors."""
        import anthropic

        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            api_error = anthropic.APIError(
                message="Rate limit exceeded",
                request=MagicMock(),
                body=None,
            )
            mock_client.messages.create = AsyncMock(side_effect=api_error)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)
            messages = [ChatMessage(role="user", content="Hello")]

            with pytest.raises(ModelAdapterError) as exc_info:
                await adapter.chat(messages)

            assert "Rate limit exceeded" in str(exc_info.value)
            assert exc_info.value.provider == ModelProvider.ANTHROPIC

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_complete_unexpected_error(
        self,
        api_key: str,
    ) -> None:
        """Test completion handles unexpected errors."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(
                side_effect=RuntimeError("Unexpected error")
            )
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)

            with pytest.raises(ModelAdapterError) as exc_info:
                await adapter.complete("Hello")

            assert "Unexpected error during completion" in str(exc_info.value)
            assert exc_info.value.provider == ModelProvider.ANTHROPIC

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_usage(self, api_key: str) -> None:
        """Test get_usage returns usage statistics."""
        adapter = AnthropicModelAdapter(api_key=api_key)
        usage = await adapter.get_usage()

        assert isinstance(usage, dict)
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_empty_messages(
        self,
        api_key: str,
        mock_response: MagicMock,
    ) -> None:
        """Test chat with empty messages list."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)
            response = await adapter.chat([])

            assert isinstance(response, ModelResponse)
            mock_client.messages.create.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_with_system_message(
        self,
        api_key: str,
        mock_response: MagicMock,
    ) -> None:
        """Test chat correctly formats system messages."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            adapter = AnthropicModelAdapter(api_key=api_key)
            messages = [
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello"),
            ]
            await adapter.chat(messages)

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][0]["content"] == "You are helpful."


class TestChatMessage:
    """Test suite for ChatMessage dataclass."""

    @pytest.mark.unit
    def test_create_message(self) -> None:
        """Test creating a chat message."""
        msg = ChatMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    @pytest.mark.unit
    def test_create_message_with_name(self) -> None:
        """Test creating a chat message with name."""
        msg = ChatMessage(role="user", content="Hello", name="Alice")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name == "Alice"


class TestModelResponse:
    """Test suite for ModelResponse dataclass."""

    @pytest.mark.unit
    def test_create_response(self) -> None:
        """Test creating a model response."""
        response = ModelResponse(
            content="Hello!",
            model="claude-sonnet-4-20250514",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        assert response.content == "Hello!"
        assert response.model == "claude-sonnet-4-20250514"
        assert response.usage["total_tokens"] == 15
        assert response.stop_reason is None

    @pytest.mark.unit
    def test_create_response_with_stop_reason(self) -> None:
        """Test creating a response with stop reason."""
        response = ModelResponse(
            content="Hello!",
            model="claude-sonnet-4-20250514",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            stop_reason="end_turn",
        )

        assert response.stop_reason == "end_turn"
