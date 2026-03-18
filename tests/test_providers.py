"""Provider abstraction tests."""

from unittest.mock import MagicMock, patch

import pytest

from fediaf_verifier.exceptions import ConfigurationError
from fediaf_verifier.providers import (
    AIProvider,
    AnthropicProvider,
    GeminiProvider,
    ProviderAPIError,
    ProviderRateLimitError,
    create_provider,
)


class TestCreateProvider:
    def test_creates_anthropic(self):
        with patch("fediaf_verifier.providers.anthropic") as mock_anth:
            mock_anth.Anthropic.return_value = MagicMock()
            p = create_provider("anthropic", "sk-test", "claude-sonnet-4-6")
            assert isinstance(p, AnthropicProvider)

    def test_creates_gemini(self):
        with patch("fediaf_verifier.providers.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            p = create_provider("gemini", "AIza-test", "gemini-3-flash")
            assert isinstance(p, GeminiProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ConfigurationError, match="Nieznany provider"):
            create_provider("openai", "key", "gpt-4")

    def test_case_insensitive(self):
        with patch("fediaf_verifier.providers.anthropic") as mock_anth:
            mock_anth.Anthropic.return_value = MagicMock()
            p = create_provider("Anthropic", "sk-test", "model")
            assert isinstance(p, AnthropicProvider)


class TestAnthropicProvider:
    @patch("fediaf_verifier.providers.anthropic")
    def test_call_returns_text(self, mock_anth):
        mock_client = MagicMock()
        mock_anth.Anthropic.return_value = mock_client

        text_block = MagicMock()
        text_block.text = '{"product_name": "Test"}'
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider("sk-test", "claude-sonnet-4-6")
        result = provider.call(
            prompt="test", media_b64="abc", media_type="image/jpeg",
            max_tokens=100,
        )

        assert result == '{"product_name": "Test"}'
        mock_client.messages.create.assert_called_once()

    @patch("fediaf_verifier.providers.anthropic")
    def test_call_pdf_document_block(self, mock_anth):
        mock_client = MagicMock()
        mock_anth.Anthropic.return_value = mock_client

        text_block = MagicMock()
        text_block.text = "{}"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider("sk-test", "model")
        provider.call(
            prompt="test", media_b64="abc",
            media_type="application/pdf", max_tokens=100,
        )

        call_args = mock_client.messages.create.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert content[0]["type"] == "document"

    @patch("fediaf_verifier.providers.anthropic")
    def test_rate_limit_wrapped(self, mock_anth):
        mock_client = MagicMock()
        mock_anth.Anthropic.return_value = mock_client
        mock_anth.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_anth.APIError = type("APIError", (Exception,), {})

        mock_client.messages.create.side_effect = (
            mock_anth.RateLimitError("rate limit")
        )

        provider = AnthropicProvider("sk-test", "model")

        with pytest.raises(ProviderRateLimitError):
            provider.call(
                prompt="test", media_b64="abc",
                media_type="image/jpeg", max_tokens=100,
            )

    @patch("fediaf_verifier.providers.anthropic")
    def test_api_error_wrapped(self, mock_anth):
        mock_client = MagicMock()
        mock_anth.Anthropic.return_value = mock_client
        mock_anth.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_anth.APIError = type("APIError", (Exception,), {})

        mock_client.messages.create.side_effect = (
            mock_anth.APIError("bad request")
        )

        provider = AnthropicProvider("sk-test", "model")

        with pytest.raises(ProviderAPIError):
            provider.call(
                prompt="test", media_b64="abc",
                media_type="image/jpeg", max_tokens=100,
            )

    @patch("fediaf_verifier.providers.anthropic")
    def test_no_text_blocks_raises(self, mock_anth):
        mock_client = MagicMock()
        mock_anth.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider("sk-test", "model")

        with pytest.raises(ProviderAPIError, match="nie zwrocilo tekstu"):
            provider.call(
                prompt="test", media_b64="abc",
                media_type="image/jpeg", max_tokens=100,
            )


class TestGeminiProvider:
    @patch("fediaf_verifier.providers.genai_types")
    @patch("fediaf_verifier.providers.genai")
    def test_call_returns_text(self, mock_genai, mock_types):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"product_name": "Test"}'
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider("AIza-test", "gemini-3-flash")
        result = provider.call(
            prompt="test", media_b64="YWJj",
            media_type="image/jpeg", max_tokens=100,
        )

        assert result == '{"product_name": "Test"}'

    @patch("fediaf_verifier.providers.genai_types")
    @patch("fediaf_verifier.providers.genai")
    def test_rate_limit_wrapped(self, mock_genai, mock_types):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_client.models.generate_content.side_effect = Exception(
            "429 Resource Exhausted"
        )

        provider = GeminiProvider("AIza-test", "model")

        with pytest.raises(ProviderRateLimitError):
            provider.call(
                prompt="test", media_b64="YWJj",
                media_type="image/jpeg", max_tokens=100,
            )

    @patch("fediaf_verifier.providers.genai_types")
    @patch("fediaf_verifier.providers.genai")
    def test_generic_error_wrapped(self, mock_genai, mock_types):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_client.models.generate_content.side_effect = Exception(
            "Invalid model name"
        )

        provider = GeminiProvider("AIza-test", "model")

        with pytest.raises(ProviderAPIError):
            provider.call(
                prompt="test", media_b64="YWJj",
                media_type="image/jpeg", max_tokens=100,
            )

    @patch("fediaf_verifier.providers.genai_types")
    @patch("fediaf_verifier.providers.genai")
    def test_empty_response_raises(self, mock_genai, mock_types):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider("AIza-test", "model")

        with pytest.raises(ProviderAPIError, match="nie zwrocilo tekstu"):
            provider.call(
                prompt="test", media_b64="YWJj",
                media_type="image/jpeg", max_tokens=100,
            )


class TestProtocol:
    def test_anthropic_satisfies_protocol(self):
        with patch("fediaf_verifier.providers.anthropic"):
            p = AnthropicProvider("key", "model")
            assert isinstance(p, AIProvider)

    @patch("fediaf_verifier.providers.genai")
    def test_gemini_satisfies_protocol(self, mock_genai):
        p = GeminiProvider("key", "model")
        assert isinstance(p, AIProvider)
