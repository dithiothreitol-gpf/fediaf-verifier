"""Configuration loading tests."""


import pytest
from pydantic import ValidationError

from fediaf_verifier.config import AppSettings


class TestAppSettings:
    def test_valid_settings(self):
        settings = AppSettings(anthropic_api_key="sk-ant-test-key")
        assert settings.anthropic_api_key == "sk-ant-test-key"
        assert settings.anthropic_model == "claude-sonnet-4-6"

    def test_missing_api_key_raises(self, monkeypatch):
        """Missing API key should raise ValidationError."""
        # Clear any env vars that might provide the key
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ValidationError, match="anthropic_api_key"):
            AppSettings(_env_file=None)  # type: ignore[call-arg]

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

        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.anthropic_api_key == "sk-ant-from-env"
        assert settings.anthropic_model == "claude-opus-4-6"
        assert settings.cross_check_tolerance == 1.0

    def test_fediaf_pdf_path_is_path(self):
        from pathlib import Path

        settings = AppSettings(anthropic_api_key="sk-ant-test")
        assert isinstance(settings.fediaf_pdf_path, Path)
