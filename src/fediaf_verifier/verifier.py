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
    PRESENTATION_CHECK_PROMPT,
    SECONDARY_CHECK_PROMPT,
    SELF_VERIFY_PROMPT,
    PRODUCT_DESCRIPTION_VERIFY_PROMPT,
    build_targeted_reread_prompt,
    build_artwork_summary_prompt,
    build_label_text_prompt,
    build_market_check_prompt,
    build_product_description_from_image_prompt,
    build_product_description_prompt,
    build_translation_prompt,
)
from fediaf_verifier.providers import (
    AIProvider,
    ProviderAPIError,
    create_provider,
)
from fediaf_verifier.utils import api_call_with_retry, extract_json


def _get_collector(settings: AppSettings):
    """Lazy-init shared DataCollector instance."""
    if not settings.data_collection_enabled:
        return None

    key = "_data_collector"
    if not hasattr(_get_collector, key):
        from fediaf_verifier.data_collector import DataCollector

        setattr(
            _get_collector,
            key,
            DataCollector(
                base_dir=settings.data_collection_dir,
                enabled=True,
            ),
        )
    return getattr(_get_collector, key)


def _self_verify(
    result_json: str,
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
    model_class: type,
    mode: str = "unknown",
    prompt_used: str = "",
) -> object:
    """Send AI result back for self-verification (reflection step).

    Asks a second AI call to compare the result against the original image
    and remove false positives, duplicates, and hallucinations.
    Also collects training data if data_collection_enabled.

    Args:
        result_json: JSON string of the initial AI result.
        label_b64: Original label image as base64.
        media_type: MIME type of the label.
        provider: AI provider for the verification call.
        settings: Application settings.
        model_class: Pydantic model class to validate the corrected result.
        mode: Verification mode name for data collection.
        prompt_used: Original prompt for data collection.

    Returns:
        Verified and corrected model instance, or None if verification
        is disabled or fails.
    """
    raw_data = json.loads(result_json)
    verified_data = None
    corrected = None

    if settings.self_verify_enabled:
        logger.info("Self-verify: verifying AI result against original image...")

        try:
            # Use string concatenation instead of .format() to avoid
            # KeyError when result_json contains curly braces
            verify_prompt = SELF_VERIFY_PROMPT + "\n\n" + result_json

            # Use same token budget as the original call (result can be large)
            max_tokens = max(
                settings.max_tokens_linguistic,
                len(result_json) // 3 + 2048,
            )

            raw = provider.call(
                prompt=verify_prompt,
                media_b64=label_b64,
                media_type=media_type,
                max_tokens=min(max_tokens, 16384),
            )
            corrected_json = extract_json(raw)
            verified_data = json.loads(corrected_json)
            corrected = model_class.model_validate(verified_data)
            logger.info("Self-verify: result corrected successfully")
        except Exception as e:
            logger.warning("Self-verify failed (using original result): {}", e)

    # Collect training data (regardless of self-verify success)
    collector = _get_collector(settings)
    if collector is not None:
        collector.record(
            mode=mode,
            model=getattr(provider, "_model", getattr(provider, "model", "unknown")),
            prompt=prompt_used,
            image_b64=label_b64,
            media_type=media_type,
            raw_response=raw_data,
            verified_response=verified_data,
        )

    return corrected


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
    return _build_enriched_report(
        extraction, compliance, secondary, settings,
        label_b64=label_b64, media_type=media_type,
        provider=secondary_provider,
    )


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

        # Self-verify: send result back to AI for false-positive removal
        corrected = _self_verify(
            result_json=json_text,
            label_b64=label_b64,
            media_type=media_type,
            provider=provider,
            settings=settings,
            model_class=ClaimsCheckReport,
            mode="claims",
            prompt_used=CLAIMS_CHECK_PROMPT,
        )
        if corrected is not None:
            report = corrected

        return ClaimsCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Claims check failed: {}", e)
        return ClaimsCheckResult(
            performed=False,
            error=f"Blad walidacji claimow: {e}",
        )


def verify_presentation(
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "PresentationCheckResult":
    """Check commercial presentation compliance (recipes, names, brand, trademarks).

    Single AI call: extracts product context, validates recipe claims,
    naming conventions (EU 767/2009 Art.17), brand regulatory compliance,
    and trademark / IP risks.
    """
    from fediaf_verifier.models.presentation_check import (
        PresentationCheckReport,
        PresentationCheckResult,
    )

    logger.info("Presentation compliance check...")

    def _call() -> PresentationCheckResult:
        raw_text = provider.call(
            prompt=PRESENTATION_CHECK_PROMPT,
            media_b64=label_b64,
            media_type=media_type,
            max_tokens=settings.max_tokens_presentation,
        )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)

        report = PresentationCheckReport.model_validate(data)

        # Self-verify: send result back to AI for false-positive removal
        corrected = _self_verify(
            result_json=json_text,
            label_b64=label_b64,
            media_type=media_type,
            provider=provider,
            settings=settings,
            model_class=PresentationCheckReport,
            mode="presentation",
            prompt_used=PRESENTATION_CHECK_PROMPT,
        )
        if corrected is not None:
            report = corrected

        return PresentationCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Presentation check failed: {}", e)
        return PresentationCheckResult(
            performed=False,
            error=f"Blad walidacji prezentacji handlowej: {e}",
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


def _validate_product_description_claims(
    report: "ProductDescriptionReport",
    ingredients: str,
    nutrients: dict | None,
) -> list["ClaimWarning"]:
    """Deterministic claim validation — Python hard rules, no AI.

    Checks the generated description against input data and FEDIAF/EU rules.
    Returns additional ClaimWarning objects to append to the report.
    """
    from fediaf_verifier.models.product_description import ClaimWarning

    warnings: list[ClaimWarning] = []
    ingredients_lower = ingredients.lower() if ingredients else ""
    full_text_lower = (report.complete_text or "").lower()

    # -- 1. Grain-free claim check -----------------------------------------------
    GRAIN_KEYWORDS = [
        "pszenica", "wheat", "jeczmien", "jęczmień", "barley",
        "owies", "oat", "zyto", "żyto", "rye",
        "kukurydza", "corn", "maize",
        "ryz", "ryż", "rice",
        "proso", "millet", "sorgo", "sorghum",
        "orkisz", "spelt",
        "cereals", "grains", "zboza", "zboża", "zboze", "zboże",
    ]
    claims_text = " ".join(report.claims_used or []).lower()
    grain_free_claimed = any(
        phrase in full_text_lower or phrase in claims_text
        for phrase in [
            "grain-free", "grain free", "bez zboz", "bez zbóż",
            "bezzbozow", "bezzbożow",
        ]
    )
    if grain_free_claimed:
        grains_found = [g for g in GRAIN_KEYWORDS if g in ingredients_lower]
        if grains_found:
            warnings.append(ClaimWarning(
                claim_text="grain-free / bez zbóż",
                warning_type="naming_rule_violation",
                explanation=(
                    f"Opis zawiera claim 'bez zbóż' ale w składnikach "
                    f"wykryto: {', '.join(grains_found)}"
                ),
                recommendation="Usuń claim 'grain-free' lub popraw skład.",
            ))

    # -- 2. Therapeutic / medicinal claim check ----------------------------------
    FORBIDDEN_THERAPEUTIC = [
        "leczy", "wyleczy", "zapobiega chorobom", "likwiduje",
        "eliminuje choroby", "terapeutycz", "lecznic", "medyczn",
        "zastepuje leczenie", "cures", "treats disease", "prevents disease",
        "therapeutic", "medicinal",
    ]
    for phrase in FORBIDDEN_THERAPEUTIC:
        if phrase in full_text_lower:
            warnings.append(ClaimWarning(
                claim_text=phrase,
                warning_type="forbidden_therapeutic",
                explanation=(
                    f"Opis zawiera zakazany claim terapeutyczny: '{phrase}'. "
                    "EU 767/2009 Art.13 zabrania claimów leczniczych."
                ),
                recommendation=(
                    "Zamień na claim funkcjonalny, np. 'wspiera trawienie' "
                    "zamiast 'leczy problemy trawienne'."
                ),
            ))

    # -- 3. "Natural" claim check ------------------------------------------------
    SYNTHETIC_INDICATORS = [
        "syntetycz", "synthetic", "artificial", "sztuczn",
        "e-", "e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9",
        "bha", "bht", "etoksychin", "ethoxyquin",
    ]
    natural_claimed = any(
        w in full_text_lower or w in claims_text
        for w in ["natural", "naturaln", "naturale", "natürlich"]
    )
    if natural_claimed and ingredients_lower:
        synthetics_found = [
            s for s in SYNTHETIC_INDICATORS if s in ingredients_lower
        ]
        if synthetics_found:
            warnings.append(ClaimWarning(
                claim_text="natural / naturalny",
                warning_type="needs_evidence",
                explanation=(
                    f"Claim 'natural' może wymagać zastrzeżenia — "
                    f"w składnikach wykryto potencjalnie syntetyczne: "
                    f"{', '.join(synthetics_found)}"
                ),
                recommendation=(
                    "Dodaj zastrzeżenie: 'z dodanymi witaminami i minerałami' "
                    "lub usuń claim 'natural'."
                ),
            ))

    # -- 4. Percentage-based naming rule check (FEDIAF 4%/14%/26%) ---------------
    import re

    # Check claims_used for "bogaty w X" / "rich in X" patterns
    # Use Unicode-aware regex for Polish characters
    _INGR_PCT_RE = re.compile(
        r'([\w\u0080-\u024F][\w\u0080-\u024F\s]*?)\s*\(?\s*(\d+(?:[.,]\d+)?)\s*%'
    )

    def _stem_match(ingredient_name: str, claim_text: str) -> bool:
        """Check if ingredient name (or its stem) appears in claim text.

        Handles Polish/German/etc. declensions by matching the first 4+ chars.
        E.g. 'łosoś' matches 'łososia', 'kurczak' matches 'kurczaka'.
        """
        if not ingredient_name or len(ingredient_name) < 3:
            return ingredient_name in claim_text
        # Try full name first
        if ingredient_name in claim_text:
            return True
        # Try stem (first N chars, min 4)
        stem_len = max(4, len(ingredient_name) - 2)
        stem = ingredient_name[:stem_len]
        return stem in claim_text

    for claim in (report.claims_used or []):
        claim_lower = claim.lower()

        # "bogaty w X" / "rich in X" → needs 14%
        if any(p in claim_lower for p in ["bogat", "rich in", "reich an"]):
            for ingredient_match in _INGR_PCT_RE.finditer(ingredients):
                ingr_name = ingredient_match.group(1).strip().lower()
                ingr_pct = float(ingredient_match.group(2).replace(",", "."))
                if _stem_match(ingr_name, claim_lower) and ingr_pct < 14:
                    warnings.append(ClaimWarning(
                        claim_text=claim,
                        warning_type="naming_rule_violation",
                        explanation=(
                            f"Claim '{claim}' wymaga min. 14% składnika "
                            f"wg FEDIAF, ale podano {ingr_pct}%."
                        ),
                        recommendation=(
                            f"Zmień na 'z {ingr_name}' (wymaga min. 4%) "
                            f"lub zwiększ udział do 14%."
                        ),
                    ))

        # "z X" / "with X" → needs 4%
        elif any(p in claim_lower for p in ["z ", "with ", "mit "]):
            for ingredient_match in _INGR_PCT_RE.finditer(ingredients):
                ingr_name = ingredient_match.group(1).strip().lower()
                ingr_pct = float(ingredient_match.group(2).replace(",", "."))
                if _stem_match(ingr_name, claim_lower) and ingr_pct < 4:
                    warnings.append(ClaimWarning(
                        claim_text=claim,
                        warning_type="naming_rule_violation",
                        explanation=(
                            f"Claim '{claim}' wymaga min. 4% składnika "
                            f"wg FEDIAF, ale podano {ingr_pct}%."
                        ),
                        recommendation="Usuń claim lub zwiększ udział do 4%.",
                    ))

    # -- 5. Species/lifestage consistency check ----------------------------------
    if report.species and ingredients:
        # If report says "cat" but description mentions dog-specific things
        species_lower = report.species.lower()
        if "cat" in species_lower or "kot" in species_lower:
            dog_words = ["dla psow", "for dogs", "für hunde", "pour chiens"]
            for dw in dog_words:
                if dw in full_text_lower:
                    warnings.append(ClaimWarning(
                        claim_text=f"Gatunek: {report.species}",
                        warning_type="unsubstantiated",
                        explanation=(
                            f"Opis jest dla kota ale zawiera zwrot '{dw}' "
                            "odnoszący się do psów."
                        ),
                        recommendation="Popraw opis — usuń odniesienia do psów.",
                    ))
        elif "dog" in species_lower or "pies" in species_lower:
            cat_words = ["dla kotow", "for cats", "für katzen", "pour chats"]
            for cw in cat_words:
                if cw in full_text_lower:
                    warnings.append(ClaimWarning(
                        claim_text=f"Gatunek: {report.species}",
                        warning_type="unsubstantiated",
                        explanation=(
                            f"Opis jest dla psa ale zawiera zwrot '{cw}' "
                            "odnoszący się do kotów."
                        ),
                        recommendation="Popraw opis — usuń odniesienia do kotów.",
                    ))

    return warnings


def _self_verify_product_description(
    result_json: str,
    provider: AIProvider,
    settings: AppSettings,
    ingredients: str,
    nutrients: dict | None,
    species: str,
    lifestage: str,
    food_type: str,
    product_name: str,
    label_b64: str = "",
    media_type: str = "",
) -> "ProductDescriptionReport | None":
    """Self-verify product description — reflection step.

    Sends the generated description back to the AI with the input data
    as ground truth, asking it to remove hallucinations and unsubstantiated
    claims. Works in both manual mode (text-only) and image mode.
    """
    from fediaf_verifier.models.product_description import (
        ProductDescriptionReport,
    )

    if not settings.self_verify_enabled:
        return None

    logger.info("Self-verify: verifying product description against input data...")

    try:
        # Build input data summary as ground truth
        nutrient_lines = []
        if nutrients:
            for k, v in nutrients.items():
                if v:
                    nutrient_lines.append(f"  {k}: {v}%")

        input_summary = (
            f"Gatunek: {species}\n"
            f"Etap zycia: {lifestage}\n"
            f"Typ karmy: {food_type}\n"
            f"Nazwa produktu: {product_name}\n"
            f"Skladniki: {ingredients}\n"
            f"Skladniki analityczne:\n"
            + ("\n".join(nutrient_lines) if nutrient_lines else "  (brak danych)")
        )

        verify_prompt = (
            PRODUCT_DESCRIPTION_VERIFY_PROMPT.format(input_data=input_summary)
            + "\n\n"
            + result_json
        )

        max_tokens = max(
            settings.max_tokens_product_desc,
            len(result_json) // 3 + 2048,
        )

        if label_b64:
            raw = provider.call(
                prompt=verify_prompt,
                media_b64=label_b64,
                media_type=media_type,
                max_tokens=min(max_tokens, 16384),
            )
        else:
            raw = provider.call(
                prompt=verify_prompt,
                max_tokens=min(max_tokens, 16384),
            )

        corrected_json = extract_json(raw)
        corrected_data = json.loads(corrected_json)
        corrected = ProductDescriptionReport.model_validate(corrected_data)
        logger.info("Self-verify: product description corrected successfully")
        return corrected
    except Exception as e:
        logger.warning(
            "Self-verify failed for product description (using original): {}", e
        )
        return None


def generate_product_description(
    provider: AIProvider,
    settings: AppSettings,
    target_language: str,
    target_language_name: str,
    tone: str,
    # Manual mode params (text-only):
    species: str = "",
    lifestage: str = "",
    food_type: str = "",
    ingredients: str = "",
    nutrients: dict | None = None,
    product_name: str = "",
    usps: str = "",
    brand: str = "",
    # Image mode params:
    label_b64: str = "",
    media_type: str = "",
) -> "ProductDescriptionResult":
    """Generate a commercial product description for e-commerce / marketing.

    3-layer verification pipeline:
      1. AI generates description
      2. AI self-verify (reflection) removes hallucinations
      3. Python deterministic rules validate claims

    Supports two input modes:
      - Image upload: pass label_b64 + media_type (AI extracts data from label)
      - Manual input: pass species, lifestage, food_type, ingredients, nutrients
    """
    from fediaf_verifier.models.product_description import (
        ProductDescriptionReport,
        ProductDescriptionResult,
    )

    logger.info(
        "Product description generation: {} ({}) [{}]...",
        target_language_name,
        target_language,
        "image" if label_b64 else "manual",
    )

    if label_b64:
        prompt = build_product_description_from_image_prompt(
            target_language=target_language,
            target_language_name=target_language_name,
            tone=tone,
        )
    else:
        prompt = build_product_description_prompt(
            species=species,
            lifestage=lifestage,
            food_type=food_type,
            ingredients=ingredients,
            nutrients=nutrients or {},
            target_language=target_language,
            target_language_name=target_language_name,
            tone=tone,
            product_name=product_name,
            usps=usps,
            brand=brand,
        )

    def _call() -> ProductDescriptionResult:
        # -- Layer 1: AI generates description -----------------------------------
        if label_b64:
            raw_text = provider.call(
                prompt=prompt,
                media_b64=label_b64,
                media_type=media_type,
                max_tokens=settings.max_tokens_product_desc,
            )
        else:
            raw_text = provider.call(
                prompt=prompt,
                max_tokens=settings.max_tokens_product_desc,
            )

        json_text = extract_json(raw_text)
        data = json.loads(json_text)
        report = ProductDescriptionReport.model_validate(data)

        # -- Layer 2: AI self-verify (reflection step) ---------------------------
        corrected = _self_verify_product_description(
            result_json=json_text,
            provider=provider,
            settings=settings,
            ingredients=ingredients,
            nutrients=nutrients,
            species=species or (report.species if report else ""),
            lifestage=lifestage or (report.lifestage if report else ""),
            food_type=food_type or (report.food_type if report else ""),
            product_name=product_name or (report.product_name if report else ""),
            label_b64=label_b64,
            media_type=media_type,
        )
        if corrected is not None:
            report = corrected

        # -- Layer 3: Deterministic claim validation (Python hard rules) ---------
        hard_warnings = _validate_product_description_claims(
            report=report,
            ingredients=ingredients or "",
            nutrients=nutrients,
        )
        if hard_warnings:
            # Merge: avoid duplicates by claim_text
            existing_claims = {
                cw.claim_text for cw in (report.claims_warnings or [])
            }
            for hw in hard_warnings:
                if hw.claim_text not in existing_claims:
                    report.claims_warnings.append(hw)
                    existing_claims.add(hw.claim_text)
            logger.info(
                "Deterministic validation added {} claim warnings",
                len(hard_warnings),
            )

        return ProductDescriptionResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Product description generation failed: {}", e)
        return ProductDescriptionResult(
            performed=False,
            error=f"Blad generowania opisu produktu: {e}",
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
    segment: str = "premium_dry",
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

        # --- Benchmarks ---
        try:
            from fediaf_verifier.benchmarks import get_benchmarks, record_scores

            report.benchmark_comparisons = get_benchmarks(
                segment, report.category_scores,
            )
            record_scores(segment, report.category_scores)
        except Exception as exc:
            logger.warning("Benchmark computation failed: {}", exc)

        return DesignAnalysisResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Design analysis failed: {}", e)
        return DesignAnalysisResult(
            performed=False,
            error=f"Blad analizy graficznej: {e}",
        )


def verify_artwork_inspection(
    img_a_b64: str,
    media_type_a: str,
    provider: AIProvider,
    settings: AppSettings,
    img_b_b64: str | None = None,
    media_type_b: str | None = None,
    pixel_diff_threshold: int = 30,
    n_colors: int = 6,
    enable_ocr: bool = True,
    enable_saliency: bool = True,
) -> "ArtworkInspectionResult":
    """Run artwork inspection: pixel diff, color, print, OCR, ICC, saliency.

    Deterministic CV analysis + optional AI summary of findings.

    Args:
        img_a_b64: Base64-encoded master/reference image.
        media_type_a: MIME type of image A.
        provider: AI provider for summary generation.
        settings: App settings.
        img_b_b64: Optional base64-encoded proof/new version.
        media_type_b: MIME type of image B.
        pixel_diff_threshold: Sensitivity for pixel change detection (0–255).
        n_colors: Number of dominant colors to extract.
        enable_ocr: Enable OCR text comparison (requires easyocr).
        enable_saliency: Enable saliency heatmap analysis.
    """
    from fediaf_verifier.artwork_inspector import run_artwork_inspection
    from fediaf_verifier.models.artwork_inspection import (
        ArtworkInspectionResult,
    )

    logger.info("Artwork inspection...")

    try:
        # Phase 1: Deterministic analysis (OpenCV / Pillow)
        report = run_artwork_inspection(
            img_a_b64=img_a_b64,
            media_type_a=media_type_a,
            img_b_b64=img_b_b64,
            media_type_b=media_type_b,
            pixel_diff_threshold=pixel_diff_threshold,
            n_colors=n_colors,
            enable_ocr=enable_ocr,
            enable_saliency=enable_saliency,
        )

        # Phase 2: AI summary of findings
        try:
            findings_data = report.model_dump(
                exclude={
                    "pixel_diff": {"diff_image_b64"},
                    "saliency": {"heatmap_b64"},
                },
                exclude_none=True,
            )
            findings_json = json.dumps(findings_data, ensure_ascii=False, indent=2)
            prompt = build_artwork_summary_prompt(findings_json)

            raw_text = provider.call(
                prompt=prompt,
                max_tokens=settings.max_tokens_artwork,
            )
            json_text = extract_json(raw_text)
            ai_data = json.loads(json_text)

            report.ai_summary = ai_data.get("ai_summary", "")
            report.ai_recommendations = ai_data.get("ai_recommendations", [])
        except Exception as e:
            logger.warning("AI summary for artwork inspection failed: {}", e)
            report.ai_summary = "Podsumowanie AI niedostepne — wyniki deterministyczne powyzej."

        return ArtworkInspectionResult(performed=True, report=report)

    except Exception as e:
        logger.error("Artwork inspection failed: {}", e)
        from fediaf_verifier.models.artwork_inspection import ArtworkInspectionResult

        return ArtworkInspectionResult(
            performed=False,
            error=f"Blad inspekcji artwork: {e}",
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

        # Self-verify: send result back to AI for false-positive removal
        corrected = _self_verify(
            result_json=json_text,
            label_b64=label_b64,
            media_type=media_type,
            provider=provider,
            settings=settings,
            model_class=LabelStructureReport,
            mode="structure",
            prompt_used=LABEL_STRUCTURE_PROMPT,
        )
        if corrected is not None:
            report = corrected

        return LabelStructureCheckResult(performed=True, report=report)

    try:
        return api_call_with_retry(_call)
    except Exception as e:
        logger.error("Label structure check failed: {}", e)
        return LabelStructureCheckResult(
            performed=False,
            error=f"Blad kontroli struktury etykiety: {e}",
        )


def _cross_validate_linguistic(report) -> "LinguisticReport":
    """Cross-validate AI linguistic issues against Hunspell (deterministic).

    Adds confidence scoring to each issue:
    - HIGH: AI + Hunspell agree the word is misspelled
    - MEDIUM: Only AI flagged it (grammar/punctuation — can't verify)
    - LOW: AI flagged but Hunspell says word is correct (possible hallucination)

    Also checks for missing diacritics that AI might have missed.
    """
    from fediaf_verifier.models import LinguisticReport

    if not report or not report.issues:
        return report

    lang = report.detected_language or ""
    if not lang:
        return report

    try:
        from fediaf_verifier.spellcheck import (
            check_diacritics_presence,
            validate_ai_linguistic_issues,
        )

        # Cross-validate existing AI issues
        issues_dicts = [iss.model_dump() for iss in report.issues]
        validated = validate_ai_linguistic_issues(
            ai_issues=issues_dicts,
            text="",  # not needed for word-level validation
            language=lang,
        )

        # Rebuild issues with confidence data
        report = LinguisticReport(
            detected_language=report.detected_language,
            detected_language_name=report.detected_language_name,
            issues=validated,
            overall_quality=report.overall_quality,
            summary=report.summary,
        )

        logger.info(
            "Cross-validation: {} issues scored (high={}, medium={}, low={})",
            len(report.issues),
            sum(1 for i in report.issues if i.confidence == "high"),
            sum(1 for i in report.issues if i.confidence == "medium"),
            sum(1 for i in report.issues if i.confidence == "low"),
        )

    except ImportError:
        logger.debug("spylls not installed — skipping deterministic cross-validation")
    except Exception as e:
        logger.warning("Cross-validation failed (non-blocking): {}", e)

    return report


def _reread_verify_issues(
    report: "LinguisticReport",
    label_b64: str,
    media_type: str,
    provider: AIProvider,
    settings: AppSettings,
) -> "LinguisticReport":
    """Reduce OCR false positives using two strategies:

    1. DETERMINISTIC (no AI call): If OCR confusion detector is high-confidence
       (>= 0.7) AND the suggestion is a valid Hunspell word → auto-dismiss.
       Same AI re-reading the same image would likely repeat the same OCR error.

    2. AI RE-READ (fallback): For medium-confidence OCR suspects (0.4-0.7),
       send the image back with a focused prompt for character-level re-read.

    Returns updated LinguisticReport with OCR false positives filtered out.
    """
    from fediaf_verifier.models import LinguisticReport
    from fediaf_verifier.spellcheck import (
        _extract_words,
        _load_dictionary,
        detect_ocr_confusion,
    )

    if not report or not report.issues:
        return report

    # Extract primary language from compound codes like "pl+sk", "pl,sk", "pl/sk"
    raw_lang = report.detected_language or ""
    lang = raw_lang.split("+")[0].split(",")[0].split("/")[0].strip().lower()
    logger.warning("REREAD: processing {} issues, raw_lang={}, lang={}", len(report.issues), raw_lang, lang)

    # Try to load Hunspell for deterministic validation of suggestions
    hunspell_dict = None
    try:
        hunspell_dict = _load_dictionary(lang)
        logger.warning("REREAD: Hunspell dict loaded: {}", hunspell_dict is not None)
    except Exception as exc:
        logger.warning("REREAD: Hunspell load failed: {}", exc)

    # Classify issues into: auto-dismiss (high OCR confidence) vs re-read (medium)
    auto_dismiss_indices: list[int] = []
    reread_candidates: list[dict] = []
    reread_indices: list[int] = []

    # Issue type keywords that indicate spelling/diacritics (AI may return
    # free-form Polish descriptions instead of standardized English codes)
    _SPELLING_KEYWORDS = {
        "spelling", "diacritics", "ortografia", "diakrytycz", "literow",
        "niekompletne", "brakuj",
    }

    def _is_spelling_or_diacritics(issue_type: str) -> bool:
        it_lower = issue_type.lower()
        return any(kw in it_lower for kw in _SPELLING_KEYWORDS)

    for idx, iss in enumerate(report.issues):
        logger.warning(
            "REREAD: issue[{}] type={}, original={!r}, suggestion={!r}",
            idx, iss.issue_type, iss.original[:50], iss.suggestion[:50],
        )
        if not _is_spelling_or_diacritics(iss.issue_type):
            logger.warning("REREAD: issue[{}] skipped (type={})", idx, iss.issue_type)
            continue
        if not iss.original or not iss.suggestion:
            logger.warning("REREAD: issue[{}] skipped (empty orig/sugg)", idx)
            continue

        ocr_check = detect_ocr_confusion(
            original=iss.original,
            suggestion=iss.suggestion,
            language=lang,
        )
        logger.warning(
            "REREAD: issue[{}] OCR check: likely={}, conf={}, type={}",
            idx, ocr_check["is_ocr_likely"], ocr_check["confidence"],
            ocr_check["confusion_type"],
        )
        if not ocr_check["is_ocr_likely"]:
            continue

        ocr_conf = ocr_check["confidence"]

        # Strategy 1: High-confidence OCR pattern + valid suggestion
        # Instead of removing, DOWNGRADE confidence to "low" with explanation.
        # This way the user sees it but knows it's likely an AI hallucination.
        # Exception: if original is ALSO a valid word → keep as-is (real error).
        if ocr_conf >= 0.7 and hunspell_dict is not None:
            # Check if original words are all valid (both sides real words = real error)
            original_words = _extract_words(iss.original)
            original_checkable = [w for w in original_words if len(w) > 2]
            original_all_valid = len(original_checkable) > 0 and all(
                hunspell_dict.lookup(w) or hunspell_dict.lookup(w.lower())
                or hunspell_dict.lookup(w.title())
                for w in original_checkable
            )
            if original_all_valid:
                # Both original and suggestion are valid words — real error, keep as-is
                logger.warning(
                    "REREAD: issue[{}] KEPT (original is also valid: {})",
                    idx, original_checkable,
                )
                continue

            # Original has invalid words + matches OCR pattern → likely hallucination
            # Downgrade to "low" confidence instead of removing
            suggestion_words = _extract_words(iss.suggestion)
            checkable = [w for w in suggestion_words if len(w) > 2]
            suggestion_valid = len(checkable) > 0 and all(
                hunspell_dict.lookup(w) or hunspell_dict.lookup(w.lower())
                or hunspell_dict.lookup(w.title())
                for w in checkable
            )
            if suggestion_valid:
                auto_dismiss_indices.append(idx)
                logger.warning("REREAD: issue[{}] DOWNGRADED to low (likely hallucination)", idx)
                continue

        # Strategy 2: Medium-confidence → queue for AI re-read
        reread_candidates.append({
            "original": iss.original,
            "suggestion": iss.suggestion,
            "context": iss.context,
            "ocr_confidence": ocr_conf,
            "confusion_type": ocr_check["confusion_type"],
        })
        reread_indices.append(idx)

    # Apply downgrades (not removals — user still sees them with "low" confidence)
    issues_updated = list(report.issues)
    for idx in auto_dismiss_indices:
        issues_updated[idx].confidence = "low"
        issues_updated[idx].verified_by = "ai_only (possible hallucination — OCR pattern match)"
        issues_updated[idx].ocr_reread_word = issues_updated[idx].suggestion

    # AI re-read for remaining candidates (only if there are any)
    if reread_candidates:
        logger.info(
            "Reread: {} issues for AI re-verification...",
            len(reread_candidates),
        )
        try:
            words_json = json.dumps(
                [{"original": c["original"], "suggestion": c["suggestion"],
                  "context": c["context"]}
                 for c in reread_candidates],
                ensure_ascii=False,
            )
            prompt = build_targeted_reread_prompt(words_json)

            raw = provider.call(
                prompt=prompt,
                media_b64=label_b64,
                media_type=media_type,
                max_tokens=settings.max_tokens_reread,
            )

            json_text = extract_json(raw)
            data = json.loads(json_text)

            reread_results = data.get("reread_results", [])

            # Build lookup: original_flagged → reread result
            reread_lookup: dict[str, dict] = {}
            for r in reread_results:
                key = r.get("original_flagged", "").strip().lower()
                if key:
                    reread_lookup[key] = r

            for issue_idx in reread_indices:
                iss = issues_updated[issue_idx]
                key = iss.original.strip().lower()

                rr = reread_lookup.get(key)
                if rr is None:
                    sugg_key = iss.suggestion.strip().lower()
                    for rk, rv in reread_lookup.items():
                        if rv.get("reread_from_image", "").strip().lower() == sugg_key:
                            rr = rv
                            break

                if rr is None:
                    continue

                is_correct = rr.get("is_correct_on_image", False)
                rr_confidence = rr.get("confidence", "low")

                if is_correct and rr_confidence in ("high", "medium"):
                    # Re-read confirms label is correct → downgrade to low
                    iss.confidence = "low"
                    iss.verified_by = "ai_only (re-read confirms image is correct)"
                    iss.ocr_reread_word = rr.get("reread_from_image", "")
                    logger.info(
                        "Reread: '{}' confirmed correct on image ('{}')",
                        iss.original, iss.ocr_reread_word,
                    )

        except Exception as e:
            logger.warning("Reread AI call failed (non-blocking): {}", e)

    downgraded = len(auto_dismiss_indices) + sum(
        1 for idx in reread_indices if issues_updated[idx].confidence == "low"
    )
    logger.info(
        "OCR filter: downgraded {} issues to 'low' confidence ({} by pattern, {} by re-read)",
        downgraded, len(auto_dismiss_indices),
        downgraded - len(auto_dismiss_indices),
    )

    return LinguisticReport(
        detected_language=report.detected_language,
        detected_language_name=report.detected_language_name,
        issues=issues_updated,
        overall_quality=report.overall_quality,
        summary=report.summary,
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

        # Self-verify: send result back to AI for false-positive removal
        corrected = _self_verify(
            result_json=json_text,
            label_b64=label_b64,
            media_type=media_type,
            provider=provider,
            settings=settings,
            model_class=LinguisticReport,
            mode="linguistic",
            prompt_used=LINGUISTIC_ONLY_PROMPT,
        )
        if corrected is not None:
            report = corrected

        # Deterministic cross-validation: Hunspell confirms/denies AI findings
        report = _cross_validate_linguistic(report)

        logger.warning(
            "PRE-REREAD: {} issues, reread_enabled={}, types={}",
            len(report.issues) if report and report.issues else 0,
            settings.reread_enabled,
            [(i.issue_type, i.original[:30], i.suggestion[:30]) for i in (report.issues or [])],
        )

        # Targeted re-read: verify OCR-suspect issues against the image
        if settings.reread_enabled:
            report = _reread_verify_issues(
                report, label_b64, media_type, provider, settings
            )

        logger.warning(
            "POST-REREAD: {} issues remaining",
            len(report.issues) if report and report.issues else 0,
        )

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

        # Self-verify: send result back to AI for false-positive removal
        corrected = _self_verify(
            result_json=json_text,
            label_b64=label_b64,
            media_type=media_type,
            provider=provider,
            settings=settings,
            model_class=MarketCheckReport,
            mode="market",
            prompt_used=prompt,
        )
        if corrected is not None:
            report = corrected

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
            ):
                if isinstance(val, str):
                    data[key] = val.lower().strip() in (
                        "true", "yes", "tak", "1", "present",
                    )
                elif isinstance(val, list):
                    data[key] = len(val) > 0

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
    label_b64: str = "",
    media_type: str = "",
    provider: AIProvider | None = None,
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

        report = LinguisticReport(
            detected_language=secondary.detected_language,
            detected_language_name=secondary.detected_language_name,
            issues=[
                iss.model_dump() if hasattr(iss, "model_dump") else iss
                for iss in secondary.linguistic_issues
            ],
            overall_quality=secondary.overall_language_quality,
            summary=secondary.language_summary,
        )

        # Deterministic cross-validation: Hunspell confirms/denies AI findings
        report = _cross_validate_linguistic(report)

        # Targeted re-read: verify OCR-suspect issues against the image
        if settings.reread_enabled and provider and label_b64:
            report = _reread_verify_issues(
                report, label_b64, media_type, provider, settings
            )

        linguistic_result = LinguisticCheckResult(
            performed=True,
            report=report,
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
