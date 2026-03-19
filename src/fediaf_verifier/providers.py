"""AI provider abstraction layer.

Supports Anthropic (Claude), Google (Gemini), and OpenAI (GPT) as
interchangeable backends.  Each provider implements the same ``call``
interface, so the verification pipeline is model-agnostic.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import anthropic

from fediaf_verifier.exceptions import ConfigurationError

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

try:
    import openai as _openai
except ImportError:  # pragma: no cover
    _openai = None  # type: ignore[assignment]

if TYPE_CHECKING:
    pass

# -- Provider exceptions (SDK-agnostic) ----------------------------------------


class ProviderRateLimitError(Exception):
    """Rate limit hit by any provider. Used for retry logic."""


class ProviderAPIError(Exception):
    """Non-rate-limit API error from any provider."""


# -- Protocol ------------------------------------------------------------------


@runtime_checkable
class AIProvider(Protocol):
    """Minimal interface every AI provider must satisfy."""

    def call(
        self,
        prompt: str,
        media_b64: str,
        media_type: str,
        max_tokens: int,
    ) -> str:
        """Send prompt + image/document and return raw text response.

        Args:
            prompt: The text prompt.
            media_b64: Base64-encoded image or PDF.
            media_type: MIME type (image/jpeg, image/png, application/pdf).
            max_tokens: Maximum tokens for the response.

        Returns:
            Raw text string (expected to contain JSON).

        Raises:
            ProviderRateLimitError: On 429 / resource exhausted.
            ProviderAPIError: On other API errors.
        """
        ...


# -- Anthropic -----------------------------------------------------------------


class AnthropicProvider:
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def call(
        self,
        prompt: str,
        media_b64: str,
        media_type: str,
        max_tokens: int,
    ) -> str:
        if media_type == "application/pdf":
            media_block: dict = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": media_b64,
                },
            }
        else:
            media_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": media_b64,
                },
            }

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            media_block,
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except anthropic.APIError as e:
            raise ProviderAPIError(str(e)) from e

        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        if not text_blocks:
            raise ProviderAPIError("API nie zwrocilo tekstu w odpowiedzi.")

        raw = text_blocks[-1]

        # Detect truncated response (hit max_tokens limit)
        if response.stop_reason == "max_tokens":
            from fediaf_verifier.utils import repair_truncated_json

            repaired = repair_truncated_json(raw)
            if repaired is not None:
                return repaired
            raise ProviderAPIError(
                "Odpowiedz AI zostala ucieta (za dluga). "
                "Sprobuj ponownie lub zmniejsz zlozonosc etykiety."
            )

        return raw


# -- Gemini --------------------------------------------------------------------


class GeminiProvider:
    """Google Gemini provider using the google-genai SDK."""

    def __init__(self, api_key: str, model: str) -> None:
        if genai is None:
            raise ConfigurationError(
                "Pakiet 'google-genai' jest wymagany dla providera Gemini. "
                "Zainstaluj: pip install google-genai"
            )
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def call(
        self,
        prompt: str,
        media_b64: str,
        media_type: str,
        max_tokens: int,
    ) -> str:
        if genai_types is None:
            raise ConfigurationError("google-genai nie zainstalowane.")

        media_bytes = base64.b64decode(media_b64)

        parts = [
            genai_types.Part.from_bytes(data=media_bytes, mime_type=media_type),
            genai_types.Part.from_text(text=prompt),
        ]

        config = genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=parts,
                config=config,
            )
        except Exception as e:
            error_str = str(e).lower()
            if any(
                kw in error_str
                for kw in ("429", "resource_exhausted", "quota", "rate")
            ):
                raise ProviderRateLimitError(str(e)) from e
            raise ProviderAPIError(str(e)) from e

        if not response.text:
            raise ProviderAPIError("Gemini nie zwrocilo tekstu w odpowiedzi.")

        raw = response.text

        # Detect truncated response (Gemini: check finish_reason)
        finish_reason = None
        if response.candidates:
            finish_reason = getattr(
                response.candidates[0], "finish_reason", None
            )
        if finish_reason and str(finish_reason).upper() in (
            "MAX_TOKENS", "LENGTH",
        ):
            from fediaf_verifier.utils import repair_truncated_json

            repaired = repair_truncated_json(raw)
            if repaired is not None:
                return repaired
            raise ProviderAPIError(
                "Odpowiedz AI zostala ucieta (za dluga). "
                "Sprobuj ponownie lub zmniejsz zlozonosc etykiety."
            )

        return raw


# -- OpenAI --------------------------------------------------------------------


class OpenAIProvider:
    """OpenAI GPT provider (GPT-5.4 family)."""

    def __init__(self, api_key: str, model: str) -> None:
        if _openai is None:
            raise ConfigurationError(
                "Pakiet 'openai' jest wymagany dla providera OpenAI. "
                "Zainstaluj: pip install openai"
            )
        self._client = _openai.OpenAI(api_key=api_key)
        self._model = model

    def call(
        self,
        prompt: str,
        media_b64: str,
        media_type: str,
        max_tokens: int,
    ) -> str:
        image_url = f"data:{media_type};base64,{media_b64}"

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
        except _openai.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except _openai.APIError as e:
            raise ProviderAPIError(str(e)) from e

        choice = response.choices[0]
        raw = choice.message.content or ""

        if not raw:
            raise ProviderAPIError("OpenAI nie zwrocilo tekstu w odpowiedzi.")

        # Detect truncated response
        if choice.finish_reason == "length":
            from fediaf_verifier.utils import repair_truncated_json

            repaired = repair_truncated_json(raw)
            if repaired is not None:
                return repaired
            raise ProviderAPIError(
                "Odpowiedz AI zostala ucieta (za dluga). "
                "Sprobuj ponownie lub zmniejsz zlozonosc etykiety."
            )

        return raw


# -- Factory -------------------------------------------------------------------

_PROVIDER_REGISTRY: dict[str, type] = {
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


def create_provider(provider_name: str, api_key: str, model: str) -> AIProvider:
    """Create a provider instance by name.

    Raises:
        ConfigurationError: If provider_name is unknown or SDK not installed.
    """
    cls = _PROVIDER_REGISTRY.get(provider_name.lower())
    if cls is None:
        raise ConfigurationError(
            f"Nieznany provider: '{provider_name}'. "
            f"Dostepne: {', '.join(_PROVIDER_REGISTRY)}"
        )
    return cls(api_key=api_key, model=model)  # type: ignore[return-value]
