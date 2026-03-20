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
        media_b64: str = "",
        media_type: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Send prompt + optional image/document and return raw text response.

        Args:
            prompt: The text prompt.
            media_b64: Base64-encoded image or PDF. Empty for text-only.
            media_type: MIME type (image/jpeg, image/png, application/pdf).
            max_tokens: Maximum tokens for the response.

        Returns:
            Raw text string (expected to contain JSON).

        Raises:
            ProviderRateLimitError: On 429 / resource exhausted.
            ProviderAPIError: On other API errors.
        """
        ...

    def call_multi(
        self,
        prompt: str,
        media_list: list[tuple[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """Send prompt with multiple images/documents.

        Args:
            prompt: The text prompt.
            media_list: List of (base64_data, mime_type) tuples.
            max_tokens: Maximum tokens for the response.

        Returns:
            Raw text string (expected to contain JSON).
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
        media_b64: str = "",
        media_type: str = "",
        max_tokens: int = 4096,
    ) -> str:
        # Build content blocks
        content: list[dict] = []

        if media_b64:
            if media_type == "application/pdf":
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": media_b64,
                    },
                })
            else:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": media_b64,
                    },
                })

        content.append({"type": "text", "text": prompt})

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
            )
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except anthropic.BadRequestError as e:
            error_msg = str(e).lower()
            if "too large" in error_msg or "too many" in error_msg or "size" in error_msg:
                raise ProviderAPIError(
                    "Plik jest za duzy dla API. Sprobuj:\n"
                    "- Wyeksportowac etykiete jako pojedyncza strone\n"
                    "- Zmniejszyc rozdzielczosc obrazu\n"
                    "- Uzyc formatu JPG zamiast PNG/PDF"
                ) from e
            raise ProviderAPIError(str(e)) from e
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

    def call_multi(
        self,
        prompt: str,
        media_list: list[tuple[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        content: list[dict] = []
        for b64_data, mime in media_list:
            if mime == "application/pdf":
                content.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": mime, "data": b64_data},
                })
            else:
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": b64_data},
                })
        content.append({"type": "text", "text": prompt})

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
            )
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except anthropic.APIError as e:
            raise ProviderAPIError(str(e)) from e

        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        if not text_blocks:
            raise ProviderAPIError("API nie zwrocilo tekstu w odpowiedzi.")
        raw = text_blocks[-1]

        if response.stop_reason == "max_tokens":
            from fediaf_verifier.utils import repair_truncated_json
            repaired = repair_truncated_json(raw)
            if repaired is not None:
                return repaired
            raise ProviderAPIError("Odpowiedz AI zostala ucieta.")
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
        media_b64: str = "",
        media_type: str = "",
        max_tokens: int = 4096,
    ) -> str:
        if genai_types is None:
            raise ConfigurationError("google-genai nie zainstalowane.")

        parts = []
        if media_b64:
            media_bytes = base64.b64decode(media_b64)
            parts.append(
                genai_types.Part.from_bytes(data=media_bytes, mime_type=media_type)
            )
        parts.append(genai_types.Part.from_text(text=prompt))

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

    def call_multi(
        self,
        prompt: str,
        media_list: list[tuple[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        if genai_types is None:
            raise ConfigurationError("google-genai nie zainstalowane.")
        parts = []
        for b64_data, mime in media_list:
            media_bytes = base64.b64decode(b64_data)
            parts.append(
                genai_types.Part.from_bytes(data=media_bytes, mime_type=mime)
            )
        parts.append(genai_types.Part.from_text(text=prompt))

        config = genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )
        try:
            response = self._client.models.generate_content(
                model=self._model, contents=parts, config=config,
            )
        except Exception as e:
            error_str = str(e).lower()
            if any(kw in error_str for kw in ("429", "resource_exhausted", "quota", "rate")):
                raise ProviderRateLimitError(str(e)) from e
            raise ProviderAPIError(str(e)) from e
        if not response.text:
            raise ProviderAPIError("Gemini nie zwrocilo tekstu.")
        return response.text


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
        media_b64: str = "",
        media_type: str = "",
        max_tokens: int = 4096,
    ) -> str:
        msg_content: list[dict] = []

        if media_b64:
            image_url = f"data:{media_type};base64,{media_b64}"
            msg_content.append({
                "type": "image_url",
                "image_url": {"url": image_url, "detail": "high"},
            })

        msg_content.append({"type": "text", "text": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": msg_content}],
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

    def call_multi(
        self,
        prompt: str,
        media_list: list[tuple[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        msg_content: list[dict] = []
        for b64_data, mime in media_list:
            image_url = f"data:{mime};base64,{b64_data}"
            msg_content.append({
                "type": "image_url",
                "image_url": {"url": image_url, "detail": "high"},
            })
        msg_content.append({"type": "text", "text": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": msg_content}],
            )
        except _openai.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except _openai.APIError as e:
            raise ProviderAPIError(str(e)) from e

        raw = response.choices[0].message.content or ""
        if not raw:
            raise ProviderAPIError("OpenAI nie zwrocilo tekstu.")
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
