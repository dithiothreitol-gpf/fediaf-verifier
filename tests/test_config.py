"""Configuration loading tests."""


import pytest
from pydantic import ValidationError

from fediaf_verifier.config import AppSettings


class TestAppSettings:
    def test_valid_settings_anthropic(self):
        settings = AppSettings(anthropic_api_key="sk-ant-test-key")
        assert settings.anthropic_api_key == "sk-ant-test-key"
        assert settings.extraction_provider == "anthropic"
        assert settings.extraction_model == "claude-sonnet-4-6"
        assert settings.secondary_provider == "anthropic"
        assert settings.secondary_model == "claude-sonnet-4-6"

    def test_valid_settings_gemini(self):
        settings = AppSettings(
            gemini_api_key="AIza-test",
            extraction_provider="gemini",
            extraction_model="gemini-3-flash",
            secondary_provider="gemini",
            secondary_model="gemini-3-flash",
        )
        assert settings.gemini_api_key == "AIza-test"
        assert settings.extraction_provider == "gemini"

    def test_mixed_providers(self):
        settings = AppSettings(
            anthropic_api_key="sk-ant-test",
            gemini_api_key="AIza-test",
            extraction_provider="gemini",
            extraction_model="gemini-3-flash",
            secondary_provider="anthropic",
            secondary_model="claude-sonnet-4-6",
        )
        assert settings.extraction_provider == "gemini"
        assert settings.secondary_provider == "anthropic"

    def test_missing_anthropic_key_when_needed(self, monkeypatch):
        """Missing Anthropic key should raise when provider requires it."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
            AppSettings(
                extraction_provider="anthropic",
                _env_file=None,  # type: ignore[call-arg]
            )

    def test_missing_gemini_key_when_needed(self, monkeypatch):
        """Missing Gemini key should raise when provider requires it."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
            AppSettings(
                anthropic_api_key="sk-ant-test",
                extraction_provider="gemini",
                _env_file=None,  # type: ignore[call-arg]
            )

    def test_no_key_needed_if_provider_not_used(self):
        """Gemini key not required if only Anthropic is configured."""
        settings = AppSettings(
            anthropic_api_key="sk-ant-test",
            extraction_provider="anthropic",
            secondary_provider="anthropic",
        )
        assert settings.gemini_api_key == ""

    def test_defaults(self):
        settings = AppSettings(anthropic_api_key="sk-ant-test")
        assert settings.max_tokens_main == 16384
        assert settings.max_tokens_cross_check == 1024
        assert settings.cross_check_tolerance == 0.5
        assert settings.auto_approve_threshold == 85
        assert settings.manual_required_threshold == 60
        assert settings.log_level == "INFO"

    def test_override_via_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-6")
        monkeypatch.setenv("CROSS_CHECK_TOLERANCE", "1.0")
        monkeypatch.setenv("EXTRACTION_PROVIDER", "anthropic")

        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.anthropic_api_key == "sk-ant-from-env"
        assert settings.anthropic_model == "claude-opus-4-6"
        assert settings.cross_check_tolerance == 1.0

    def test_fediaf_pdf_path_is_path(self):
        from pathlib import Path

        settings = AppSettings(anthropic_api_key="sk-ant-test")
        assert isinstance(settings.fediaf_pdf_path, Path)
