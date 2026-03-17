"""Cross-check module tests with mocked API client."""

from unittest.mock import MagicMock

import anthropic
import pytest

from fediaf_verifier.config import AppSettings
from fediaf_verifier.cross_check import cross_check_nutrients
from fediaf_verifier.models import NutrientsOnly, NutrientValues


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def _settings() -> AppSettings:
    return AppSettings(
        anthropic_api_key="sk-ant-test",
        cross_check_tolerance=0.5,
        _env_file=None,  # type: ignore[call-arg]
    )


def _mock_create_response(model) -> MagicMock:
    """Build a mock messages.create() response with JSON text block."""
    text_block = MagicMock()
    text_block.text = model.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [text_block]
    return mock_response


class TestCrossCheckNutrients:
    def test_no_discrepancies_passes(self, mock_client, _settings):
        """When cross-check reads same values, result passes."""
        cross_model = NutrientsOnly(
            crude_protein=22.0,
            crude_fat=8.0,
            moisture=10.0,
            reading_notes="all clear",
        )
        mock_client.messages.create.return_value = _mock_create_response(
            cross_model
        )

        main_nutrients = NutrientValues(
            crude_protein=22.0,
            crude_fat=8.0,
            moisture=10.0,
        )

        result = cross_check_nutrients(
            "b64data", "image/jpeg", main_nutrients, mock_client, _settings
        )

        assert result.passed is True
        assert len(result.discrepancies) == 0
        assert result.reading_notes == "all clear"

    def test_discrepancy_detected(self, mock_client, _settings):
        """When values differ by more than tolerance, flag discrepancy."""
        cross_model = NutrientsOnly(
            crude_protein=24.0,  # differs from main by 2.0
            crude_fat=8.0,
            moisture=10.0,
        )
        mock_client.messages.create.return_value = _mock_create_response(
            cross_model
        )

        main_nutrients = NutrientValues(
            crude_protein=22.0,
            crude_fat=8.0,
            moisture=10.0,
        )

        result = cross_check_nutrients(
            "b64data", "image/jpeg", main_nutrients, mock_client, _settings
        )

        assert result.passed is False
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].nutrient == "crude_protein"
        assert result.discrepancies[0].difference == 2.0

    def test_none_values_skipped(self, mock_client, _settings):
        """None values in either reading should be skipped."""
        cross_model = NutrientsOnly(
            crude_protein=None,
            crude_fat=8.0,
        )
        mock_client.messages.create.return_value = _mock_create_response(
            cross_model
        )

        main_nutrients = NutrientValues(
            crude_protein=22.0,
            crude_fat=8.0,
        )

        result = cross_check_nutrients(
            "b64data", "image/jpeg", main_nutrients, mock_client, _settings
        )

        # crude_protein skipped (cross is None), fat matches
        assert result.passed is True
        assert len(result.discrepancies) == 0

    def test_api_error_returns_none_passed(self, mock_client, _settings):
        """API errors are non-blocking — return passed=None."""
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="test error",
            request=MagicMock(),
            body=None,
        )

        main_nutrients = NutrientValues(crude_protein=22.0)

        result = cross_check_nutrients(
            "b64data", "image/jpeg", main_nutrients, mock_client, _settings
        )

        assert result.passed is None
        assert result.error is not None

    def test_within_tolerance_passes(self, mock_client, _settings):
        """Values within tolerance (0.5) should pass."""
        cross_model = NutrientsOnly(
            crude_protein=22.3,  # differs by 0.3, within 0.5 tolerance
        )
        mock_client.messages.create.return_value = _mock_create_response(
            cross_model
        )

        main_nutrients = NutrientValues(crude_protein=22.0)

        result = cross_check_nutrients(
            "b64data", "image/jpeg", main_nutrients, mock_client, _settings
        )

        assert result.passed is True
