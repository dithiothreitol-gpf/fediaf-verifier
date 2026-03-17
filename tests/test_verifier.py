"""Verifier pipeline tests with mocked API client."""

from unittest.mock import MagicMock, patch

import pytest

from fediaf_verifier.config import AppSettings
from fediaf_verifier.models import (
    ComplianceStatus,
    CrossCheckResult,
    Discrepancy,
    EULabellingCheck,
    ExtractionConfidence,
    LinguisticCheckResult,
    NutrientValues,
    Product,
    VerificationReport,
)
from fediaf_verifier.verifier import verify_label


@pytest.fixture
def _settings() -> AppSettings:
    return AppSettings(anthropic_api_key="sk-ant-test", _env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def compliant_ai_report() -> VerificationReport:
    return VerificationReport(
        product=Product(species="dog", lifestage="adult", food_type="dry"),
        extracted_nutrients=NutrientValues(
            crude_protein=22.0,
            crude_fat=8.0,
            moisture=10.0,
            calcium=1.2,
            phosphorus=0.9,
        ),
        extraction_confidence=ExtractionConfidence.HIGH,
        compliance_score=95,
        status=ComplianceStatus.COMPLIANT,
        issues=[],
        eu_labelling_check=EULabellingCheck(
            ingredients_listed=True,
            analytical_constituents_present=True,
            manufacturer_info=True,
            net_weight_declared=True,
            species_clearly_stated=True,
            batch_or_date_present=True,
        ),
        recommendations=[],
    )


def _mock_ai_response(report: VerificationReport) -> MagicMock:
    """Build a mock messages.create() response containing JSON text."""
    text_block = MagicMock()
    text_block.text = report.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [text_block]
    return mock_response


class TestVerifyLabel:
    @patch("fediaf_verifier.verifier.perform_linguistic_check")
    @patch("fediaf_verifier.verifier.cross_check_nutrients")
    def test_compliant_label_no_human_review(
        self,
        mock_cross_check,
        mock_ling_check,
        mock_client,
        _settings,
        compliant_ai_report,
    ):
        """Compliant label with high confidence should not require human review."""
        mock_client.messages.create.return_value = _mock_ai_response(
            compliant_ai_report
        )

        mock_cross_check.return_value = CrossCheckResult(passed=True)
        mock_ling_check.return_value = LinguisticCheckResult(performed=True)

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
            fediaf_b64="fediaf_b64",
        )

        assert result.status == ComplianceStatus.COMPLIANT
        assert result.requires_human_review is False
        assert len(result.hard_rule_flags) == 0
        assert result.linguistic_check_result.performed is True

    @patch("fediaf_verifier.verifier.perform_linguistic_check")
    @patch("fediaf_verifier.verifier.cross_check_nutrients")
    def test_hard_rules_override_ai_status(
        self, mock_cross_check, mock_ling_check, mock_client, _settings
    ):
        """If AI says COMPLIANT but hard rules find critical issue, override."""
        ai_report = VerificationReport(
            product=Product(species="dog", lifestage="adult", food_type="dry"),
            extracted_nutrients=NutrientValues(
                crude_protein=15.0,  # Below 18% DM minimum
                crude_fat=8.0,
                moisture=10.0,
            ),
            extraction_confidence=ExtractionConfidence.HIGH,
            compliance_score=90,
            status=ComplianceStatus.COMPLIANT,
            issues=[],
            eu_labelling_check=EULabellingCheck(
                ingredients_listed=True,
                analytical_constituents_present=True,
                manufacturer_info=True,
                net_weight_declared=True,
                species_clearly_stated=True,
                batch_or_date_present=True,
            ),
        )

        mock_client.messages.create.return_value = _mock_ai_response(ai_report)
        mock_cross_check.return_value = CrossCheckResult(passed=True)
        mock_ling_check.return_value = LinguisticCheckResult(performed=True)

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
            fediaf_b64="fediaf_b64",
        )

        assert result.status == ComplianceStatus.NON_COMPLIANT
        assert result.compliance_score <= 49
        assert len(result.hard_rule_flags) > 0
        assert any(
            f.code == "CRUDE_PROTEIN_BELOW_MIN" for f in result.hard_rule_flags
        )

    @patch("fediaf_verifier.verifier.perform_linguistic_check")
    @patch("fediaf_verifier.verifier.cross_check_nutrients")
    def test_low_confidence_requires_human_review(
        self, mock_cross_check, mock_ling_check, mock_client, _settings
    ):
        """Low extraction confidence should trigger human review."""
        ai_report = VerificationReport(
            product=Product(species="dog", lifestage="adult", food_type="dry"),
            extracted_nutrients=NutrientValues(crude_protein=22.0, moisture=10.0),
            extraction_confidence=ExtractionConfidence.LOW,
            compliance_score=80,
            status=ComplianceStatus.COMPLIANT,
            issues=[],
            eu_labelling_check=EULabellingCheck(
                ingredients_listed=True,
                analytical_constituents_present=True,
                manufacturer_info=True,
                net_weight_declared=True,
                species_clearly_stated=True,
                batch_or_date_present=True,
            ),
        )

        mock_client.messages.create.return_value = _mock_ai_response(ai_report)
        mock_cross_check.return_value = CrossCheckResult(passed=True)
        mock_ling_check.return_value = LinguisticCheckResult(performed=True)

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
            fediaf_b64="fediaf_b64",
        )

        assert result.requires_human_review is True

    @patch("fediaf_verifier.verifier.perform_linguistic_check")
    @patch("fediaf_verifier.verifier.cross_check_nutrients")
    def test_cross_check_failure_triggers_review(
        self,
        mock_cross_check,
        mock_ling_check,
        mock_client,
        _settings,
        compliant_ai_report,
    ):
        """Cross-check discrepancies should trigger human review."""
        mock_client.messages.create.return_value = _mock_ai_response(
            compliant_ai_report
        )

        mock_cross_check.return_value = CrossCheckResult(
            passed=False,
            discrepancies=[
                Discrepancy(
                    nutrient="crude_protein",
                    main_value=22.0,
                    cross_value=18.0,
                    difference=4.0,
                )
            ],
        )
        mock_ling_check.return_value = LinguisticCheckResult(performed=True)

        result = verify_label(
            label_b64="b64data",
            media_type="image/jpeg",
            settings=_settings,
            client=mock_client,
            fediaf_b64="fediaf_b64",
        )

        assert result.requires_human_review is True
