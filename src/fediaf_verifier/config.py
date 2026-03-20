"""Application settings via pydantic-settings."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables and .env file.

    Per-task provider configuration allows mixing AI backends:

        EXTRACTION_PROVIDER=gemini
        EXTRACTION_MODEL=gemini-3-flash
        SECONDARY_PROVIDER=anthropic
        SECONDARY_MODEL=claude-sonnet-4-6

    Backward compatible: old ANTHROPIC_API_KEY + ANTHROPIC_MODEL still works.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # -- API keys (provide at least one for the providers you use) --
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # -- Per-task provider + model configuration --
    extraction_provider: str = "anthropic"
    extraction_model: str = "claude-sonnet-4-6"
    secondary_provider: str = "anthropic"
    secondary_model: str = "claude-sonnet-4-6"

    # -- Legacy (backward compat) --
    anthropic_model: str = "claude-sonnet-4-6"

    # Paths
    fediaf_pdf_path: Path = Path("data/fediaf_guidelines_2021.pdf")

    # Token limits
    max_tokens_main: int = 16384
    max_tokens_cross_check: int = 1024

    # Cross-check tolerance (percentage points)
    cross_check_tolerance: float = 0.5

    # UI thresholds
    auto_approve_threshold: int = 85
    manual_required_threshold: int = 60

    # Linguistic check (cross-check + linguistic combined — needs headroom)
    max_tokens_linguistic: int = 8192

    # Translation mode
    max_tokens_translation: int = 8192

    # Design analysis mode
    max_tokens_design: int = 12288

    # Claims vs Composition check
    max_tokens_claims: int = 12288

    # Label text generation
    max_tokens_label_text: int = 12288

    # Per-market compliance check
    max_tokens_market: int = 12288

    # Label diff (version comparison)
    max_tokens_diff: int = 16384

    # EAN/barcode extraction
    max_tokens_ean: int = 2048

    # Label structure check
    max_tokens_structure: int = 12288

    # Per-market compliance check
    max_tokens_market: int = 12288

    # Self-verification (reflection step) — doubles API calls but reduces false positives
    self_verify_enabled: bool = True

    # Logging
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _validate_provider_keys(self) -> "AppSettings":
        """Ensure required API keys are present for configured providers."""
        providers_needed = {self.extraction_provider, self.secondary_provider}

        if "anthropic" in providers_needed and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY wymagany — extraction_provider lub "
                "secondary_provider ustawiony na 'anthropic'."
            )
        if "gemini" in providers_needed and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY wymagany — extraction_provider lub "
                "secondary_provider ustawiony na 'gemini'."
            )
        if "openai" in providers_needed and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY wymagany — extraction_provider lub "
                "secondary_provider ustawiony na 'openai'."
            )
        return self


def get_settings() -> AppSettings:
    """Create AppSettings instance.

    Raises pydantic ValidationError if required configuration is missing.
    """
    return AppSettings()  # type: ignore[call-arg]
