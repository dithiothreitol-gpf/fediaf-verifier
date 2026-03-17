"""Linguistic check module tests with mocked API client."""

from unittest.mock import MagicMock

import anthropic
import pytest

from fediaf_verifier.config import AppSettings
from fediaf_verifier.linguistic_check import perform_linguistic_check
from fediaf_verifier.models import (
    LinguisticIssue,
    LinguisticIssueType,
    LinguisticReport,
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def _settings() -> AppSettings:
    return AppSettings(
        anthropic_api_key="sk-ant-test",
        max_tokens_linguistic=4096,
        _env_file=None,  # type: ignore[call-arg]
    )


def _mock_create_response(model) -> MagicMock:
    """Build a mock messages.create() response with JSON text block."""
    text_block = MagicMock()
    text_block.text = model.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [text_block]
    return mock_response


class TestPerformLinguisticCheck:
    def test_no_issues_detected(self, mock_client, _settings):
        """Clean label text should return performed=True with empty issues."""
        report = LinguisticReport(
            detected_language="pl",
            detected_language_name="polski",
            issues=[],
            overall_quality="excellent",
            summary="Tekst na etykiecie jest poprawny jezykowo.",
        )
        mock_client.messages.create.return_value = _mock_create_response(report)

        result = perform_linguistic_check(
            "b64data", "image/jpeg", mock_client, _settings
        )

        assert result.performed is True
        assert result.report is not None
        assert len(result.report.issues) == 0
        assert result.report.overall_quality == "excellent"
        assert result.error is None

    def test_spelling_issues_detected(self, mock_client, _settings):
        """Spelling errors should be reported."""
        report = LinguisticReport(
            detected_language="pl",
            detected_language_name="polski",
            issues=[
                LinguisticIssue(
                    issue_type=LinguisticIssueType.SPELLING,
                    original="karme",
                    suggestion="karm\u0119",
                    context="Karma dla pies\u00f3w. Podawaj karme codziennie.",
                    explanation="B\u0142\u0119dna forma biernika.",
                ),
            ],
            overall_quality="good",
            summary="Jeden b\u0142\u0105d ortograficzny.",
        )
        mock_client.messages.create.return_value = _mock_create_response(report)

        result = perform_linguistic_check(
            "b64data", "image/jpeg", mock_client, _settings
        )

        assert result.performed is True
        assert result.report is not None
        assert len(result.report.issues) == 1
        assert result.report.issues[0].issue_type == LinguisticIssueType.SPELLING

    def test_diacritics_issues_detected(self, mock_client, _settings):
        """Missing diacritical marks should be flagged."""
        report = LinguisticReport(
            detected_language="pl",
            detected_language_name="polski",
            issues=[
                LinguisticIssue(
                    issue_type=LinguisticIssueType.DIACRITICS,
                    original="bialko",
                    suggestion="bia\u0142ko",
                    context="Sk\u0142adniki analityczne: bialko surowe 22%",
                    explanation="Brakuj\u0105cy znak diakrytyczny: l -> \u0142.",
                ),
                LinguisticIssue(
                    issue_type=LinguisticIssueType.DIACRITICS,
                    original="zywienie",
                    suggestion="\u017cywienie",
                    context="Odpowiednie zywienie Twojego psa",
                    explanation="Brakuj\u0105cy znak diakrytyczny: z -> \u017c.",
                ),
            ],
            overall_quality="needs_review",
            summary="Brakuj\u0105ce znaki diakrytyczne.",
        )
        mock_client.messages.create.return_value = _mock_create_response(report)

        result = perform_linguistic_check(
            "b64data", "image/jpeg", mock_client, _settings
        )

        assert result.performed is True
        assert result.report is not None
        assert len(result.report.issues) == 2
        assert all(
            i.issue_type == LinguisticIssueType.DIACRITICS
            for i in result.report.issues
        )
        assert result.report.overall_quality == "needs_review"

    def test_api_error_non_blocking(self, mock_client, _settings):
        """API errors should return performed=False, not raise."""
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="test error",
            request=MagicMock(),
            body=None,
        )

        result = perform_linguistic_check(
            "b64data", "image/jpeg", mock_client, _settings
        )

        assert result.performed is False
        assert result.report is None
        assert result.error is not None

    def test_multiple_issue_types(self, mock_client, _settings):
        """Multiple issue types should be detected simultaneously."""
        report = LinguisticReport(
            detected_language="pl",
            detected_language_name="polski",
            issues=[
                LinguisticIssue(
                    issue_type=LinguisticIssueType.SPELLING,
                    original="psuf",
                    suggestion="ps\u00f3w",
                    context="Karma dla psuf",
                    explanation="Literowka.",
                ),
                LinguisticIssue(
                    issue_type=LinguisticIssueType.GRAMMAR,
                    original="dla piesow",
                    suggestion="dla ps\u00f3w",
                    context="Karma sucha dla piesow",
                    explanation="B\u0142\u0119dna odmiana.",
                ),
                LinguisticIssue(
                    issue_type=LinguisticIssueType.TERMINOLOGY,
                    original="protein",
                    suggestion="bia\u0142ko",
                    context="Sk\u0142ad: protein 22%",
                    explanation="Mieszanie angielskiego z polskim.",
                ),
            ],
            overall_quality="poor",
            summary="Liczne b\u0142\u0119dy.",
        )
        mock_client.messages.create.return_value = _mock_create_response(report)

        result = perform_linguistic_check(
            "b64data", "image/jpeg", mock_client, _settings
        )

        assert result.performed is True
        assert result.report is not None
        assert len(result.report.issues) == 3
        types = {i.issue_type for i in result.report.issues}
        assert LinguisticIssueType.SPELLING in types
        assert LinguisticIssueType.GRAMMAR in types
        assert LinguisticIssueType.TERMINOLOGY in types
        assert result.report.overall_quality == "poor"

    def test_pdf_label_uses_document_block(self, mock_client, _settings):
        """PDF labels should use document block type."""
        report = LinguisticReport(
            detected_language="pl",
            detected_language_name="polski",
            issues=[],
            overall_quality="excellent",
            summary="OK",
        )
        mock_client.messages.create.return_value = _mock_create_response(report)

        perform_linguistic_check(
            "b64data", "application/pdf", mock_client, _settings
        )

        call_args = mock_client.messages.create.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert content[0]["type"] == "document"
