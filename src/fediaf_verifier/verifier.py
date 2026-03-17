"""FEDIAF label verification pipeline — orchestrates all 5 reliability layers.

Layers:
  1. Structured outputs + confidence scoring  -> messages.parse(output_format=...)
  2. Cross-validation of numeric values       -> cross_check_nutrients()
  3. Deterministic FEDIAF rules                   -> hard_check()
  4. Human-in-the-loop (logic in app.py)          -> requires_human_review flag
  5. Reference test suite                         -> tests/test_accuracy.py
"""

import anthropic
from loguru import logger

from fediaf_verifier.config import AppSettings
from fediaf_verifier.cross_check import cross_check_nutrients
from fediaf_verifier.exceptions import APIError
from fediaf_verifier.linguistic_check import perform_linguistic_check
from fediaf_verifier.models import (
    ComplianceStatus,
    CrossCheckResult,
    EnrichedReport,
    ExtractionConfidence,
    Issue,
    LinguisticCheckResult,
    Severity,
    VerificationReport,
)
from fediaf_verifier.prompts import SYSTEM_PROMPT_BASE, build_trend_instruction
from fediaf_verifier.rules import hard_check, merge_with_ai_issues
from fediaf_verifier.utils import extract_json


def create_client(settings: AppSettings) -> anthropic.Anthropic:
    """Create Anthropic client from settings."""
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def verify_label(
    label_b64: str,
    media_type: str,
    settings: AppSettings,
    client: anthropic.Anthropic,
    fediaf_b64: str = "",
    market: str | None = None,
) -> EnrichedReport:
    """Full verification pipeline with all 5 reliability layers.

    Args:
        label_b64: Label image/document encoded as base64.
        media_type: MIME type of the label.
        settings: Application settings.
        client: Anthropic client instance.
        fediaf_b64: FEDIAF guidelines PDF encoded as base64.
        market: Target market country or None.

    Returns:
        EnrichedReport with all pipeline additions.

    Raises:
        APIError: If the main verification API call fails.
    """
    # -- Layer 1: AI verification with structured output + confidence scoring ----------
    ai_report = _ai_verify(label_b64, media_type, market, client, settings)

    # Mark all AI issues with source
    for issue in ai_report.issues:
        if issue.source is None:
            issue.source = "AI"

    # -- Layer 2: Cross-validation of numeric values -----------------------------------
    logger.info("Running cross-check (Layer 2)...")
    cross_result = cross_check_nutrients(
        label_b64, media_type, ai_report.extracted_nutrients, client, settings
    )

    # -- Linguistic check ----------------------------------------------------------------
    logger.info("Running linguistic check...")
    linguistic_result = perform_linguistic_check(
        label_b64, media_type, client, settings
    )

    # -- Layer 3: Deterministic FEDIAF rules -------------------------------------------
    logger.info("Running deterministic rules (Layer 3)...")
    hard_flags = hard_check(ai_report.product, ai_report.extracted_nutrients)
    merged_issues = merge_with_ai_issues(list(ai_report.issues), hard_flags)

    # Adjust status if hard rules found critical issues that AI missed
    updated_status = ai_report.status
    updated_score = ai_report.compliance_score
    if (
        any(f.severity == Severity.CRITICAL for f in hard_flags)
        and ai_report.status == ComplianceStatus.COMPLIANT
    ):
        updated_status = ComplianceStatus.NON_COMPLIANT
        updated_score = min(ai_report.compliance_score, 49)

    # -- Layer 4: Determine human review requirement -----------------------------------
    reliability_flags = _assess_reliability(
        ai_report, cross_result, hard_flags, linguistic_result
    )
    requires_human = _requires_human_review(
        updated_score,
        ai_report.extraction_confidence,
        updated_status,
        cross_result,
        reliability_flags,
        settings,
    )

    # -- Construct enriched report -----------------------------------------------------
    return EnrichedReport(
        **ai_report.model_dump(exclude={"issues", "status", "compliance_score"}),
        issues=merged_issues,
        status=updated_status,
        compliance_score=updated_score,
        hard_rule_flags=hard_flags,
        cross_check_result=cross_result,
        linguistic_check_result=linguistic_result,
        reliability_flags=reliability_flags,
        requires_human_review=requires_human,
    )


def _ai_verify(
    label_b64: str,
    media_type: str,
    market: str | None,
    client: anthropic.Anthropic,
    settings: AppSettings,
) -> VerificationReport:
    """Layer 1: Main AI verification. FEDIAF tables embedded in system prompt."""
    system_prompt = SYSTEM_PROMPT_BASE
    if market:
        system_prompt += "\n\n" + build_trend_instruction(market)

    # Build label content block based on media type
    if media_type == "application/pdf":
        label_block: dict = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": label_b64,
            },
        }
    else:
        label_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": label_b64,
            },
        }

    # Tools for market trends (web search)
    tools: list[dict] | None = None
    if market:
        tools = [{"type": "web_search_20250305", "name": "web_search"}]

    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens_main,
            system=system_prompt,
            tools=tools if tools else anthropic.NOT_GIVEN,
            messages=[
                {
                    "role": "user",
                    "content": [
                        label_block,
                        {
                            "type": "text",
                            "text": (
                                f"Zweryfikuj te etykiete produktu pet food.\n"
                                f"Rynek: {market if market else 'nie okreslono'}.\n"
                                f"Zwroc kompletny raport JSON z ocena confidence."
                            ),
                        },
                    ],
                }
            ],
        )

        # Extract last text block (skip tool_use / thinking blocks)
        text_blocks = [
            b.text for b in response.content if hasattr(b, "text")
        ]
        if not text_blocks:
            raise APIError("API nie zwrocilo tekstu w odpowiedzi.")

        # Use the last text block — earlier blocks may be preamble/thinking
        raw_text = text_blocks[-1]
        json_text = extract_json(raw_text)
        return VerificationReport.model_validate_json(json_text)

    except anthropic.APIError as e:
        logger.error("Main verification API call failed: {}", e)
        raise APIError(f"Blad API podczas weryfikacji: {e}") from e
    except Exception as e:
        logger.error("Failed to parse AI response: {}", e)
        raise APIError(f"Blad parsowania odpowiedzi AI: {e}") from e


def _assess_reliability(
    report: VerificationReport,
    cross_check: CrossCheckResult,
    hard_flags: list[Issue],
    linguistic_result: LinguisticCheckResult | None = None,
) -> list[str]:
    """Assess result reliability and return warning flags.

    Does not modify the result — only informs the UI about risks.
    """
    flags: list[str] = []

    if report.extraction_confidence == ExtractionConfidence.LOW:
        flags.append(
            "Niska pewnosc odczytu — znaczna czesc wartosci moze byc blednie "
            "odczytana z obrazu. Zalecana weryfikacja z oryginalna etykieta."
        )
    elif report.extraction_confidence == ExtractionConfidence.MEDIUM:
        flags.append(
            "Srednia pewnosc odczytu — pojedyncze wartosci odczytane z watpliwoscia."
        )

    if report.values_requiring_manual_check:
        flags.append(
            f"Wartosci wymagajace sprawdzenia: "
            f"{', '.join(report.values_requiring_manual_check)}"
        )

    if cross_check.passed is False:
        for d in cross_check.discrepancies:
            flags.append(
                f"Rozbieznosc w odczycie {d.nutrient}: "
                f"glowny odczyt {d.main_value}%, "
                f"weryfikacja krzyzowa {d.cross_value}% "
                f"(roznica {d.difference}%). "
                "Sprawdz oryginal."
            )

    if cross_check.passed is None:
        flags.append(
            "Weryfikacja krzyzowa nie zostala wykonana — "
            "wyniki opieraja sie wylacznie na glownym odczycie."
        )

    if hard_flags:
        flags.append(
            f"Reguly deterministyczne FEDIAF wykryly {len(hard_flags)} "
            "dodatkowych problemow niezaleznie od analizy AI."
        )

    if (
        linguistic_result
        and linguistic_result.performed
        and linguistic_result.report
        and linguistic_result.report.overall_quality == "poor"
    ):
        flags.append(
            "Weryfikacja jezykowa wykryla liczne bledy na etykiecie "
            "— tekst wymaga gruntownej korekty."
        )

    return flags


def _requires_human_review(
    score: int,
    confidence: ExtractionConfidence,
    status: ComplianceStatus,
    cross_check: CrossCheckResult,
    reliability_flags: list[str],
    settings: AppSettings,
) -> bool:
    """Determine if the result requires human specialist review."""
    return (
        score < settings.manual_required_threshold
        or confidence == ExtractionConfidence.LOW
        or status == ComplianceStatus.REQUIRES_REVIEW
        or cross_check.passed is False
        or len(reliability_flags) >= 2
    )
