"""FEDIAF label verification pipeline — 2-call architecture.

Call 1: AI extracts raw data from label (what it sees)
Python: Deterministic compliance analysis (FEDIAF, EU, packaging rules)
Call 2: AI cross-checks nutrients + linguistic verification
Python: Merge into final EnrichedReport
"""

import json

from loguru import logger

from fediaf_verifier.compliance import (
    ComplianceResult,
    analyze_compliance,
    build_cross_check_result,
)
from fediaf_verifier.config import AppSettings
from fediaf_verifier.exceptions import APIError
from fediaf_verifier.models import (
    ComplianceStatus,
    CrossCheckResult,
    EnrichedReport,
    ExtractionConfidence,
    LabelExtraction,
    LinguisticCheckResult,
    SecondaryCheck,
)
from fediaf_verifier.prompts import (
    EXTRACTION_PROMPT,
    LINGUISTIC_ONLY_PROMPT,
    SECONDARY_CHECK_PROMPT,
)
from fediaf_verifier.providers import (
    AIProvider,
    ProviderAPIError,
    create_provider,
)
from fediaf_verifier.utils import api_call_with_retry, extract_json


def create_providers(
    settings: AppSettings,
) -> tuple[AIProvider, AIProvider]:
    """Create provider instances for extraction and secondary check."""
    extraction_key = _get_api_key(settings, settings.extraction_provider)
    secondary_key = _get_api_key(settings, settings.secondary_provider)

    extraction_provider = create_provider(
        settings.extraction_provider,
        extraction_key,
        settings.extraction_model,
    )
    secondary_provider = create_provider(
        settings.secondary_provider,
        secondary_key,
        settings.secondary_model,
    )
    return extraction_provider, secondary_provider


def _get_api_key(settings: AppSettings, provider: str) -> str:
    """Get API key for a given provider name."""
    if provider == "anthropic":
        return settings.anthropic_api_key
    if provider == "gemini":
        return settings.gemini_api_key
    msg = f"Nieznany provider: {provider}"
    raise APIError(msg)


def verify_label(
    label_b64: str,
    media_type: str,
    settings: AppSettings,
    extraction_provider: AIProvider,
    secondary_provider: AIProvider,
    fediaf_b64: str = "",
    market: str | None = None,
) -> EnrichedReport:
    """Full verification pipeline: 2 AI calls + deterministic analysis.

    Args:
        label_b64: Label image/document encoded as base64.
        media_type: MIME type of the label.
        settings: Application settings.
        extraction_provider: AI provider for data extraction (Call 1).
        secondary_provider: AI provider for cross-check + linguistic (Call 2).
        fediaf_b64: Unused (kept for API compat). FEDIAF tables in prompt.
        market: Target market country or None.

    Returns:
        EnrichedReport with all analysis results.
    """
    # -- CALL 1: Extract raw data from label -----------------------------------
    logger.info("Call 1: Extracting label data...")
    extraction = _extract_label_data(
        label_b64, media_type, extraction_provider, settings
    )

    # -- PYTHON: Deterministic compliance analysis -----------------------------
    logger.info("Running deterministic compliance analysis...")
    compliance = analyze_compliance(extraction)

    # -- CALL 2: Cross-check + linguistic (with rate limit retry) --------------
    logger.info("Call 2: Cross-check + linguistic verification...")
    secondary = _secondary_check(
        label_b64, media_type, secondary_provider, settings
    )

    # -- PYTHON: Build final report --------------------------------------------
    return _build_enriched_report(extraction, compliance, secondary, settings)


def verify_linguistic_only(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> LinguisticCheckResult:
    """Standalone linguistic verification — no FEDIAF/EU analysis.

    Single AI call focused exclusively on language quality.
    """
    logger.info("Linguistic-only verification...")

    def _call() -> LinguisticCheckResult:
        raw_text = provider.call(
            prompt=LINGUISTIC_ONLY_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_linguistic,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        from fediaf_verifier.models import LinguisticReport

        report = LinguisticReport.model_validate(data)
        return LinguisticCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Linguistic-only check failed: {}", e)
        return LinguisticCheckResult(
            performed=False, error=f"Blad weryfikacji jezykowej: {e}"
        )


# -- Call 1: Extraction --------------------------------------------------------


def _extract_label_data(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> LabelExtraction:
    """Call 1: Extract all visible data from label. No compliance judgments."""

    def _call() -> LabelExtraction:
        raw_text = provider.call(
            prompt=EXTRACTION_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_main,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        # Normalize booleans (AI might return "yes"/"tak" instead of true)
        for key, val in list(data.items()):
            if (
                key.startswith("has_")
                or key in (
                    "is_raw_product",
                    "contains_insect_protein",
                    "font_legibility_ok",
                    "translations_complete",
                    "country_codes_present",
                    "polish_text_complete",
                )
            ) and isinstance(val, str):
                data[key] = val.lower().strip() in (
                    "true", "yes", "tak", "1", "present",
                )

        return LabelExtraction.model_validate(data)

    try:
        return api_call_with_retry(_call)
    except ProviderAPIError as e:
        logger.error("Extraction API call failed: {}", e)
        raise APIError(f"Blad API podczas ekstrakcji: {e}") from e
    except Exception as e:
        logger.error("Failed to parse extraction response: {}", e)
        raise APIError(
            "Nie udalo sie odczytac danych z etykiety. "
            "Sprobuj innego zdjecia lub formatu."
        ) from e


# -- Call 2: Secondary check (cross-check + linguistic) ------------------------


def _secondary_check(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> SecondaryCheck | None:
    """Call 2: Cross-check nutrients + linguistic verification. Non-blocking."""

    def _call() -> SecondaryCheck:
        raw_text = provider.call(
            prompt=SECONDARY_CHECK_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_linguistic,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)
        return SecondaryCheck.model_validate(data)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.warning("Secondary check failed (non-blocking): {}", e)
        return None


# -- Build final report --------------------------------------------------------


def _build_enriched_report(
    extraction: LabelExtraction,
    compliance: ComplianceResult,
    secondary: SecondaryCheck | None,
    settings: AppSettings,
) -> EnrichedReport:
    """Assemble all results into the final EnrichedReport."""
    # Cross-check comparison
    cross_result = build_cross_check_result(
        extraction, secondary, settings.cross_check_tolerance
    )

    # Linguistic result
    linguistic_result = LinguisticCheckResult(performed=False)
    if secondary and secondary.linguistic_issues is not None:
        from fediaf_verifier.models import LinguisticReport

        linguistic_result = LinguisticCheckResult(
            performed=True,
            report=LinguisticReport(
                detected_language=secondary.detected_language,
                detected_language_name=secondary.detected_language_name,
                issues=secondary.linguistic_issues,
                overall_quality=secondary.overall_language_quality,
                summary=secondary.language_summary,
            ),
        )

    # Reliability flags
    reliability_flags = _assess_reliability(
        compliance, cross_result, linguistic_result
    )

    # Human review determination
    requires_human = _requires_human_review(
        compliance.score,
        compliance.confidence,
        compliance.status,
        cross_result,
        reliability_flags,
        settings,
    )

    return EnrichedReport(
        product=compliance.product,
        extracted_nutrients=compliance.nutrients,
        ingredients_list=extraction.ingredients,
        extraction_confidence=compliance.confidence,
        values_requiring_manual_check=extraction.values_requiring_check,
        compliance_score=compliance.score,
        status=compliance.status,
        issues=compliance.issues,
        eu_labelling_check=compliance.eu_check,
        packaging_check=compliance.packaging,
        recommendations=compliance.recommendations,
        market_trends=None,  # TODO: market trends as separate optional call
        hard_rule_flags=[
            i for i in compliance.issues if i.source == "HARD_RULE"
        ],
        cross_check_result=cross_result,
        linguistic_check_result=linguistic_result,
        reliability_flags=reliability_flags,
        requires_human_review=requires_human,
    )


def _assess_reliability(
    compliance: ComplianceResult,
    cross_check: CrossCheckResult,
    linguistic: LinguisticCheckResult,
) -> list[str]:
    """Assess result reliability and return warning flags."""
    flags: list[str] = []

    if compliance.confidence == ExtractionConfidence.LOW:
        flags.append(
            "Niska pewnosc odczytu — znaczna czesc wartosci moze byc blednie "
            "odczytana. Zalecana weryfikacja z oryginalem."
        )
    elif compliance.confidence == ExtractionConfidence.MEDIUM:
        flags.append(
            "Srednia pewnosc odczytu — pojedyncze wartosci watpliwe."
        )

    if cross_check.passed is False:
        for d in cross_check.discrepancies:
            flags.append(
                f"Rozbieznosc: {d.nutrient} — "
                f"odczyt {d.main_value}% vs weryfikacja {d.cross_value}% "
                f"(roznica {d.difference}%)"
            )

    if cross_check.passed is None:
        flags.append(
            "Weryfikacja krzyzowa nie zostala wykonana."
        )

    hard_count = sum(1 for i in compliance.issues if i.source == "HARD_RULE")
    if hard_count:
        flags.append(
            f"Reguly deterministyczne wykryly {hard_count} problemow."
        )

    if (
        linguistic.performed
        and linguistic.report
        and linguistic.report.overall_quality == "poor"
    ):
        flags.append("Tekst na etykiecie wymaga gruntownej korekty jezykowej.")

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
