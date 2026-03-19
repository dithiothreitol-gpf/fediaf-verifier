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
    CLAIMS_CHECK_PROMPT,
    DESIGN_ANALYSIS_PROMPT,
    EAN_EXTRACTION_PROMPT,
    EXTRACTION_PROMPT,
    LABEL_DIFF_PROMPT,
    LABEL_STRUCTURE_PROMPT,
    LINGUISTIC_ONLY_PROMPT,
    SECONDARY_CHECK_PROMPT,
    build_label_text_prompt,
    build_market_check_prompt,
    build_translation_prompt,
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
    if provider == "openai":
        return settings.openai_api_key
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


def verify_label_diff(
    old_b64: str,
    old_media_type: str,
    new_b64: str,
    new_media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "LabelDiffResult":
    """Compare two label versions and identify changes.

    Uses call_multi() to send both images in a single request.
    """
    from fediaf_verifier.models.label_diff import (
        LabelDiffReport,
        LabelDiffResult,
    )

    logger.info("Label diff comparison...")

    def _call() -> LabelDiffResult:
        raw_text = provider.call_multi(
            prompt=LABEL_DIFF_PROMPT,
            media_list=[
                (old_b64, old_media_type),
                (new_b64, new_media_type),
            ],
            max_tokens=settings.max_tokens_diff,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = LabelDiffReport.model_validate(data)
        return LabelDiffResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Label diff failed: {}", e)
        return LabelDiffResult(
            performed=False,
            error=f"Blad porownania wersji: {e}",
        )


def verify_translation(
    target_language: str,
    target_language_name: str,
    provider: AIProvider,
    settings: AppSettings,
    label_b64: str = "",
    media_type: str = "",
    source_text: str = "",
    user_notes: str = "",
) -> "TranslationResult":
    """Translate label content to target language.

    Supports two input modes:
      - File upload: pass label_b64 + media_type
      - Text input: pass source_text (max 2000 chars)
    """
    from fediaf_verifier.models.translation import (
        TranslationReport,
        TranslationResult,
    )

    logger.info(
        "Translation: {} -> {}...",
        "file" if label_b64 else "text",
        target_language,
    )

    prompt = build_translation_prompt(
        target_language=target_language,
        target_language_name=target_language_name,
        user_notes=user_notes,
        source_text=source_text,
    )

    def _call() -> TranslationResult:
        if label_b64:
            raw_text = provider.call(
                prompt=prompt,
                media_b64=label_b64,
                media_type=media_type,
                max_tokens=settings.max_tokens_translation,
            )
        else:
            raw_text = provider.call(
                prompt=prompt,
                max_tokens=settings.max_tokens_translation,
            )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = TranslationReport.model_validate(data)
        return TranslationResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Translation failed: {}", e)
        return TranslationResult(
            performed=False,
            error=f"Blad tlumaczenia: {e}",
        )


def verify_claims(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "ClaimsCheckResult":
    """Check consistency of marketing claims vs actual composition.

    Single AI call: extracts claims and ingredients, validates each claim,
    checks EU 767/2009 naming rules, grain-free consistency, and
    detects forbidden therapeutic claims.
    """
    from fediaf_verifier.models.claims_check import (
        ClaimsCheckReport,
        ClaimsCheckResult,
    )

    logger.info("Claims vs Composition check...")

    def _call() -> ClaimsCheckResult:
        raw_text = provider.call(
            prompt=CLAIMS_CHECK_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_claims,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = ClaimsCheckReport.model_validate(data)
        return ClaimsCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Claims check failed: {}", e)
        return ClaimsCheckResult(
            performed=False,
            error=f"Blad walidacji claimow: {e}",
        )


def generate_label_text(
    species: str,
    lifestage: str,
    food_type: str,
    ingredients: str,
    nutrients: dict,
    target_language: str,
    target_language_name: str,
    provider: AIProvider,
    settings: AppSettings,
    product_name: str = "",
) -> "LabelTextResult":
    """Generate complete label text in the target language.

    Text-only AI call (no image). Uses ingredients and nutrients data
    to produce EU 767/2009 compliant label text.

    Args:
        species: Target species (e.g. "dog", "cat").
        lifestage: Lifestage (e.g. "adult", "puppy").
        food_type: Food type (e.g. "dry", "wet").
        ingredients: Ingredients list as text.
        nutrients: Dict of analytical constituents.
        target_language: ISO 639-1 code (e.g. "en", "de").
        target_language_name: Full language name (e.g. "English").
        provider: AI provider instance.
        settings: Application settings.
        product_name: Optional product name.

    Returns:
        LabelTextResult with generated label text.
    """
    from fediaf_verifier.models.label_text import (
        LabelTextReport,
        LabelTextResult,
    )

    logger.info(
        "Label text generation: {} ({})...",
        target_language_name,
        target_language,
    )

    prompt = build_label_text_prompt(
        species=species,
        lifestage=lifestage,
        food_type=food_type,
        ingredients=ingredients,
        nutrients=nutrients,
        target_language=target_language,
        target_language_name=target_language_name,
        product_name=product_name,
    )

    def _call() -> LabelTextResult:
        raw_text = provider.call(
            prompt=prompt,
            max_tokens=settings.max_tokens_label_text,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = LabelTextReport.model_validate(data)
        return LabelTextResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Label text generation failed: {}", e)
        return LabelTextResult(
            performed=False,
            error=f"Blad generowania tekstu etykiety: {e}",
        )


def verify_ean(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "EANCheckResult":
    """Extract and validate barcodes/QR codes from label image.

    Phase 1: AI extracts barcode numbers from image.
    Phase 2: Python validates check digits deterministically.
    """
    from fediaf_verifier.ean_validator import (
        get_country_from_prefix,
        validate_ean13,
        validate_ean8,
    )
    from fediaf_verifier.models.ean_check import (
        EANCheckReport,
        EANCheckResult,
        EANResult,
        QRCodeResult,
    )

    logger.info("EAN/barcode check...")

    def _call() -> EANCheckResult:
        raw_text = provider.call(
            prompt=EAN_EXTRACTION_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_ean,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        # AI returns raw barcode data — now validate with Python
        ai_barcodes = data.get("barcodes", [])
        ai_qr = data.get("qr_codes", [])
        ai_summary = data.get("summary", "")

        ean_results: list[EANResult] = []
        for bc in ai_barcodes:
            if not isinstance(bc, dict):
                continue
            number = str(bc.get("barcode_number", "")).strip()
            bc_type = str(bc.get("barcode_type", "unknown"))
            readable = bc.get("barcode_readable", True)

            # Deterministic validation
            valid = False
            expected = ""
            if len(number) == 13:
                valid, expected = validate_ean13(number)
                if bc_type == "unknown":
                    bc_type = "EAN-13"
            elif len(number) == 8:
                valid, expected = validate_ean8(number)
                if bc_type == "unknown":
                    bc_type = "EAN-8"

            prefix, country = get_country_from_prefix(number)

            ean_results.append(EANResult(
                barcode_number=number,
                barcode_type=bc_type,
                barcode_readable=readable,
                check_digit_valid=valid,
                expected_check_digit=expected,
                country_prefix=prefix,
                country_name=country,
            ))

        qr_results = [
            QRCodeResult.model_validate(qr)
            for qr in ai_qr
            if isinstance(qr, dict)
        ]

        all_valid = all(r.check_digit_valid for r in ean_results) if ean_results else False

        report = EANCheckReport(
            ean_results=ean_results,
            qr_codes=qr_results,
            barcodes_found=len(ean_results),
            all_valid=all_valid,
            summary=ai_summary,
        )
        return EANCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("EAN check failed: {}", e)
        return EANCheckResult(
            performed=False,
            error=f"Blad walidacji kodow: {e}",
        )


def verify_design_analysis(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "DesignAnalysisResult":
    """Analyze label graphic design against packaging best practices."""
    from fediaf_verifier.models.design_analysis import (
        DesignAnalysisReport,
        DesignAnalysisResult,
    )

    logger.info("Design analysis...")

    def _call() -> DesignAnalysisResult:
        raw_text = provider.call(
            prompt=DESIGN_ANALYSIS_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_design,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = DesignAnalysisReport.model_validate(data)
        return DesignAnalysisResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Design analysis failed: {}", e)
        return DesignAnalysisResult(
            performed=False,
            error=f"Blad analizy graficznej: {e}",
        )


def verify_label_structure(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "LabelStructureCheckResult":
    """Standalone label structure & font completeness check.

    Single AI call focused on language section structure and glyph issues.
    """
    from fediaf_verifier.models.label_structure import (
        LabelStructureCheckResult,
        LabelStructureReport,
    )

    logger.info("Label structure & font check...")

    def _call() -> LabelStructureCheckResult:
        raw_text = provider.call(
            prompt=LABEL_STRUCTURE_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_structure,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = LabelStructureReport.model_validate(data)
        return LabelStructureCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Label structure check failed: {}", e)
        return LabelStructureCheckResult(
            performed=False,
            error=f"Blad kontroli struktury etykiety: {e}",
        )


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


def verify_market_compliance(
    label_b64: str,
    media_type: str,
    market_code: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "MarketCheckResult":
    """Check label compliance against per-market regulatory requirements.

    Single AI call that verifies the label against base EU 767/2009
    plus country-specific rules loaded from market_rules.py.

    Args:
        label_b64: Label image/document encoded as base64.
        media_type: MIME type of the label.
        market_code: ISO 3166-1 alpha-2 code (e.g. "DE", "FR").
        provider: AI provider instance.
        settings: Application settings.

    Returns:
        MarketCheckResult with compliance report or error.
    """
    from fediaf_verifier.market_rules import MARKET_RULES
    from fediaf_verifier.models.market_check import (
        MarketCheckReport,
        MarketCheckResult,
    )

    market_code = market_code.upper()
    rules = MARKET_RULES.get(market_code, {})
    market_name = rules.get("name", market_code)

    logger.info("Market compliance check: {} ({})...", market_name, market_code)

    prompt = build_market_check_prompt(
        market_code=market_code,
        market_name=market_name,
    )

    def _call() -> MarketCheckResult:
        raw_text = provider.call(
            prompt=prompt,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_market,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = MarketCheckReport.model_validate(data)
        return MarketCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Market compliance check failed: {}", e)
        return MarketCheckResult(
            performed=False,
            error=f"Blad walidacji rynkowej ({market_code}): {e}",
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
