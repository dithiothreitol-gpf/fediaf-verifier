"""Verifier pipeline tests with mocked API calls."""

from unittest.mock import MagicMock, patch

import pytest

from fediaf_verifier.config import AppSettings
from fediaf_verifier.models import (
    ComplianceStatus,
    LabelExtraction,
    SecondaryCheck,
)
from fediaf_verifier.verifier import verify_label


@pytest.fixture
def _settings() -> AppSettings:
    return AppSettings(anthropic_api_key="sk-ant-test", _env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def mock_client():
    return MagicMock()


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


def _mock_extraction_response(extraction: LabelExtraction) -> MagicMock:
    text_block = MagicMock()
    text_block.text = extraction.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [text_block]
    return mock_response


def _mock_secondary_response(secondary: SecondaryCheck) -> MagicMock:
    text_block = MagicMock()
    text_block.text = secondary.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [text_block]
    return mock_response


class TestVerifyLabel:
    def test_compliant_label(self, mock_client, _settings, compliant_extraction):
        """Compliant label with all elements should score high."""
        secondary = SecondaryCheck(
            cross_crude_protein=22.0,
            cross_crude_fat=8.0,
            detected_language="pl",
            detected_language_name="polski",
            overall_language_quality="excellent",
            language_summary="OK",
        )

        mock_client.messages.create.side_effect = [
            _mock_extraction_response(compliant_extraction),
            _mock_secondary_response(secondary),
        ]

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
        )

        assert result.status == ComplianceStatus.COMPLIANT
        assert result.compliance_score >= 70
        assert result.requires_human_review is False
        assert result.product.species.value == "dog"

    def test_protein_below_min_detected(self, mock_client, _settings):
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

        mock_client.messages.create.side_effect = [
            _mock_extraction_response(extraction),
            _mock_secondary_response(secondary),
        ]

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
        )

        assert any(
            i.code == "CRUDE_PROTEIN_BELOW_MIN" for i in result.issues
        )
        assert result.compliance_score < 100

    @patch("fediaf_verifier.utils.time.sleep")
    def test_secondary_failure_non_blocking(
        self, mock_sleep, mock_client, _settings, compliant_extraction
    ):
        """If Call 2 fails, pipeline still completes."""
        import anthropic as anth

        mock_client.messages.create.side_effect = [
            _mock_extraction_response(compliant_extraction),
            anth.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            ),
            anth.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            ),
            anth.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            ),
        ]

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
        )

        # Pipeline should still return a valid report
        assert result.product.species.value == "dog"
        assert result.cross_check_result.passed is None
        assert result.linguistic_check_result.performed is False
