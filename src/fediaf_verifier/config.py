"""Application settings via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables and .env file.

    Required:
        ANTHROPIC_API_KEY — your Anthropic API key

    All other fields have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API
    anthropic_api_key: str
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

    # Linguistic check
    max_tokens_linguistic: int = 4096

    # Logging
    log_level: str = "INFO"


def get_settings() -> AppSettings:
    """Create AppSettings instance.

    Raises pydantic ValidationError with a clear message if ANTHROPIC_API_KEY is missing.
    """
    return AppSettings()  # type: ignore[call-arg]
