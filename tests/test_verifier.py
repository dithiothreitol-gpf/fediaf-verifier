"""Verifier pipeline tests with mocked providers."""

from unittest.mock import MagicMock, patch

import pytest

from fediaf_verifier.config import AppSettings
from fediaf_verifier.models import (
    ComplianceStatus,
    LabelExtraction,
    SecondaryCheck,
)
from fediaf_verifier.providers import ProviderAPIError, ProviderRateLimitError
from fediaf_verifier.verifier import verify_label, verify_linguistic_only


@pytest.fixture
def _settings() -> AppSettings:
    return AppSettings(
        anthropic_api_key="sk-ant-test",
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture
def mock_extraction_provider():
    return MagicMock(spec=["call"])


@pytest.fixture
def mock_secondary_provider():
    return MagicMock(spec=["call"])


@pytest.fixture
def compliant_extraction() -> LabelExtraction:
    return LabelExtraction(
        species="dog",
        lifestage="adult",
        food_type_text="dry",
        crude_protein=22.0,
        crude_fat=8.0,
        moisture=10.0,
        calcium=1.2,
        phosphorus=0.9,
        has_ingredients_list=True,
        has_analytical_constituents=True,
        has_manufacturer_info=True,
        has_net_weight=True,
        has_species_stated=True,
        has_batch_number=True,
        has_feeding_guidelines=True,
        has_free_contact_info=True,
        has_establishment_number=True,
        product_classification_text="complete",
        extraction_confidence="HIGH",
    )


class TestVerifyLabel:
    def test_compliant_label(
        self,
        mock_extraction_provider,
        mock_secondary_provider,
        _settings,
        compliant_extraction,
    ):
        """Compliant label with all elements should score high."""
        secondary = SecondaryCheck(
            cross_crude_protein=22.0,
            cross_crude_fat=8.0,
            detected_language="pl",
            detected_language_name="polski",
            overall_language_quality="excellent",
            language_summary="OK",
        )

        mock_extraction_provider.call.return_value = (
            compliant_extraction.model_dump_json()
        )
        mock_secondary_provider.call.return_value = (
            secondary.model_dump_json()
        )

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            extraction_provider=mock_extraction_provider,
            secondary_provider=mock_secondary_provider,
        )

        assert result.status == ComplianceStatus.COMPLIANT
        assert result.compliance_score >= 70
        assert result.requires_human_review is False
        assert result.product.species.value == "dog"

    def test_protein_below_min_detected(
        self,
        mock_extraction_provider,
        mock_secondary_provider,
        _settings,
    ):
        """Low protein should be caught by deterministic rules."""
        extraction = LabelExtraction(
            species="dog",
            lifestage="adult",
            food_type_text="dry",
            crude_protein=15.0,
            crude_fat=8.0,
            moisture=10.0,
            has_ingredients_list=True,
            has_analytical_constituents=True,
            has_manufacturer_info=True,
            has_net_weight=True,
            has_species_stated=True,
            has_batch_number=True,
            has_feeding_guidelines=True,
            has_free_contact_info=True,
            has_establishment_number=True,
            product_classification_text="complete",
        )
        secondary = SecondaryCheck(
            cross_crude_protein=15.0,
            detected_language="pl",
            detected_language_name="polski",
            overall_language_quality="good",
            language_summary="OK",
        )

        mock_extraction_provider.call.return_value = (
            extraction.model_dump_json()
        )
        mock_secondary_provider.call.return_value = (
            secondary.model_dump_json()
        )

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            extraction_provider=mock_extraction_provider,
            secondary_provider=mock_secondary_provider,
        )

        assert any(
            i.code == "CRUDE_PROTEIN_BELOW_MIN" for i in result.issues
        )
        assert result.compliance_score < 100

    @patch("fediaf_verifier.utils.time.sleep")
    def test_secondary_failure_non_blocking(
        self,
        mock_sleep,
        mock_extraction_provider,
        mock_secondary_provider,
        _settings,
        compliant_extraction,
    ):
        """If Call 2 fails, pipeline still completes."""
        mock_extraction_provider.call.return_value = (
            compliant_extraction.model_dump_json()
        )
        mock_secondary_provider.call.side_effect = ProviderRateLimitError(
            "rate limit"
        )

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            extraction_provider=mock_extraction_provider,
            secondary_provider=mock_secondary_provider,
        )

        # Pipeline should still return a valid report
        assert result.product.species.value == "dog"
        assert result.cross_check_result.passed is None
        assert result.linguistic_check_result.performed is False


class TestVerifyLinguisticOnly:
    def test_successful_check(self, mock_secondary_provider, _settings):
        """Standalone linguistic check returns valid result."""
        mock_secondary_provider.call.return_value = (
            '{"detected_language": "pl",'
            '"detected_language_name": "polski",'
            '"issues": [],'
            '"overall_quality": "excellent",'
            '"summary": "Tekst bez bledow."}'
        )

        result = verify_linguistic_only(
            label_b64="b64data",
            media_type="image/jpeg",
            provider=mock_secondary_provider,
            settings=_settings,
        )

        assert result.performed is True
        assert result.report is not None
        assert result.report.detected_language == "pl"
        assert result.report.overall_quality == "excellent"
        assert len(result.report.issues) == 0

    def test_with_issues(self, mock_secondary_provider, _settings):
        """Linguistic check with spelling issues."""
        mock_secondary_provider.call.return_value = (
            '{"detected_language": "pl",'
            '"detected_language_name": "polski",'
            '"issues": [{"issue_type": "spelling",'
            '"original": "orginalny", "suggestion": "oryginalny",'
            '"context": "orginalny sklad", "explanation": "literowka"}],'
            '"overall_quality": "needs_review",'
            '"summary": "Znaleziono bledy."}'
        )

        result = verify_linguistic_only(
            label_b64="b64data",
            media_type="image/jpeg",
            provider=mock_secondary_provider,
            settings=_settings,
        )

        assert result.performed is True
        assert len(result.report.issues) == 1
        assert result.report.issues[0].issue_type == "spelling"
        assert result.report.overall_quality == "needs_review"

    @patch("fediaf_verifier.utils.time.sleep")
    def test_api_failure_returns_error(
        self, mock_sleep, mock_secondary_provider, _settings
    ):
        """API failure returns performed=False with error message."""
        mock_secondary_provider.call.side_effect = ProviderAPIError(
            "model not found"
        )

        result = verify_linguistic_only(
            label_b64="b64data",
            media_type="image/jpeg",
            provider=mock_secondary_provider,
            settings=_settings,
        )

        assert result.performed is False
        assert result.error is not None
        assert "Blad" in result.error
