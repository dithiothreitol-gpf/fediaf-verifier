"""Deterministic compliance analysis engine — zero AI.

Takes raw LabelExtraction and produces compliance results using
Python rules, FEDIAF thresholds, and EU regulation checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fediaf_verifier.models import (
    ComplianceStatus,
    CrossCheckResult,
    Discrepancy,
    EULabellingCheck,
    ExtractionConfidence,
    Issue,
    LabelExtraction,
    NutrientValues,
    PackagingCheck,
    Product,
    ProductClassification,
    SecondaryCheck,
    Severity,
)
from fediaf_verifier.rules import hard_check
from fediaf_verifier.utils import fuzzy_lookup

# -- Species / lifestage / food_type mapping -------------------------------------------

_SPECIES_MAP: dict[str, str] = {
    "dog": "dog", "pies": "dog", "psy": "dog", "hund": "dog",
    "cat": "cat", "kot": "cat", "koty": "cat", "katze": "cat",
    "other": "other", "unknown": "unknown", "inny": "other",
}

_LIFESTAGE_MAP: dict[str, str] = {
    "puppy": "puppy", "szczenię": "puppy", "szczenie": "puppy",
    "szczeniak": "puppy", "welpe": "puppy", "junior": "puppy",
    "kitten": "kitten", "kocię": "kitten", "kocie": "kitten",
    "adult": "adult", "dorosły": "adult", "dorosly": "adult",
    "senior": "senior", "starszy": "senior",
    "all_stages": "all_stages", "all stages": "all_stages",
    "all life stages": "all_stages", "wszystkie": "all_stages",
    "unknown": "unknown",
}

_FOOD_TYPE_MAP: dict[str, str] = {
    "dry": "dry", "sucha": "dry", "trocken": "dry",
    "wet": "wet", "mokra": "wet", "nass": "wet",
    "semi_moist": "semi_moist", "semi-moist": "semi_moist",
    "półwilgotna": "semi_moist", "polwilgotna": "semi_moist",
    "treat": "treat", "przysmak": "treat",
    "supplement": "supplement", "suplement": "supplement",
    "unknown": "unknown",
}

_CLASSIFICATION_MAP: dict[str, str] = {
    "complete": "complete", "pełnoporcjowa": "complete", "pelnoporcjowa": "complete",
    "complementary": "complementary", "uzupełniająca": "complementary",
    "uzupelniajaca": "complementary",
    "treat": "treat", "przysmak": "treat",
    "not_stated": "not_stated",
}

# -- Grain keywords for claim checking ------------------------------------------------

_GRAIN_KEYWORDS = {
    "pszenica", "wheat", "żyto", "rye", "jęczmień", "barley",
    "owies", "oats", "kukurydza", "corn", "maize", "ryż", "rice",
    "proso", "millet", "sorgo", "sorghum", "zboże", "grain", "cereal",
}


@dataclass
class ComplianceResult:
    """Output of deterministic compliance analysis."""

    product: Product
    nutrients: NutrientValues
    eu_check: EULabellingCheck
    packaging: PackagingCheck
    issues: list[Issue] = field(default_factory=list)
    score: int = 100
    status: ComplianceStatus = ComplianceStatus.COMPLIANT
    confidence: ExtractionConfidence = ExtractionConfidence.HIGH
    recommendations: list[str] = field(default_factory=list)


def analyze_compliance(extraction: LabelExtraction) -> ComplianceResult:
    """Full deterministic compliance analysis from raw extraction."""
    # Step 1: Map raw text to typed models
    product = _build_product(extraction)
    nutrients = _build_nutrients(extraction)
    eu_check = _build_eu_check(extraction)
    packaging = _build_packaging(extraction)
    confidence = _map_confidence(extraction.extraction_confidence)

    # Step 2: Collect issues
    issues: list[Issue] = []

    # FEDIAF nutritional rules (reuse existing hard_check)
    fediaf_issues = hard_check(product, nutrients)
    issues.extend(fediaf_issues)

    # EU labelling issues
    issues.extend(_check_eu_issues(eu_check))

    # Packaging issues
    issues.extend(_check_packaging_issues(packaging, extraction))

    # Claims consistency
    issues.extend(_check_claims(extraction))

    # Step 3: Calculate score deterministically
    score = calculate_score(issues)

    # Step 4: Determine status
    status = _determine_status(score)

    # Step 5: Generate recommendations
    recommendations = _generate_recommendations(issues)

    return ComplianceResult(
        product=product,
        nutrients=nutrients,
        eu_check=eu_check,
        packaging=packaging,
        issues=issues,
        score=score,
        status=status,
        confidence=confidence,
        recommendations=recommendations,
    )


def calculate_score(issues: list[Issue]) -> int:
    """Deterministic compliance score from issue list."""
    score = 100
    for issue in issues:
        if issue.severity == Severity.CRITICAL:
            score -= 15
        elif issue.severity == Severity.WARNING:
            score -= 5
        elif issue.severity == Severity.INFO:
            score -= 1
    return max(0, min(100, score))


def build_cross_check_result(
    extraction: LabelExtraction,
    secondary: SecondaryCheck | None,
    tolerance: float,
) -> CrossCheckResult:
    """Compare main extraction nutrients with cross-check re-read."""
    if secondary is None:
        return CrossCheckResult(passed=None)

    fields = [
        ("crude_protein", extraction.crude_protein, secondary.cross_crude_protein),
        ("crude_fat", extraction.crude_fat, secondary.cross_crude_fat),
        ("crude_fibre", extraction.crude_fibre, secondary.cross_crude_fibre),
        ("moisture", extraction.moisture, secondary.cross_moisture),
        ("crude_ash", extraction.crude_ash, secondary.cross_crude_ash),
        ("calcium", extraction.calcium, secondary.cross_calcium),
        ("phosphorus", extraction.phosphorus, secondary.cross_phosphorus),
    ]

    discrepancies: list[Discrepancy] = []
    values: dict[str, float | None] = {}

    for name, main_val, cross_val in fields:
        values[name] = cross_val
        if main_val is not None and cross_val is not None:
            diff = abs(main_val - cross_val)
            if diff > tolerance:
                discrepancies.append(Discrepancy(
                    nutrient=name,
                    main_value=main_val,
                    cross_value=cross_val,
                    difference=round(diff, 2),
                ))

    return CrossCheckResult(
        passed=len(discrepancies) == 0,
        discrepancies=discrepancies,
        cross_check_values=values,
        reading_notes=secondary.cross_reading_notes,
    )


# -- Private helpers -------------------------------------------------------------------


def _build_product(ext: LabelExtraction) -> Product:
    return Product(
        name=ext.product_name,
        brand=ext.brand,
        species=fuzzy_lookup(ext.species or "unknown", _SPECIES_MAP),
        lifestage=fuzzy_lookup(ext.lifestage or "unknown", _LIFESTAGE_MAP),
        food_type=fuzzy_lookup(ext.food_type_text or "unknown", _FOOD_TYPE_MAP),
        net_weight=ext.net_weight,
    )


def _build_nutrients(ext: LabelExtraction) -> NutrientValues:
    return NutrientValues(
        crude_protein=ext.crude_protein,
        crude_fat=ext.crude_fat,
        crude_fibre=ext.crude_fibre,
        moisture=ext.moisture,
        crude_ash=ext.crude_ash,
        calcium=ext.calcium,
        phosphorus=ext.phosphorus,
    )


def _build_eu_check(ext: LabelExtraction) -> EULabellingCheck:
    return EULabellingCheck(
        ingredients_listed=ext.has_ingredients_list,
        analytical_constituents_present=ext.has_analytical_constituents,
        manufacturer_info=ext.has_manufacturer_info,
        net_weight_declared=ext.has_net_weight,
        species_clearly_stated=ext.has_species_stated,
        batch_or_date_present=ext.has_batch_number or ext.has_best_before_date,
    )


def _build_packaging(ext: LabelExtraction) -> PackagingCheck:
    cls_text = ext.product_classification_text or "not_stated"
    cls_mapped = fuzzy_lookup(cls_text, _CLASSIFICATION_MAP)
    try:
        classification = ProductClassification(cls_mapped)
    except ValueError:
        classification = ProductClassification.NOT_STATED

    return PackagingCheck(
        feeding_guidelines_present=ext.has_feeding_guidelines,
        storage_instructions_present=ext.has_storage_instructions,
        product_classification=classification,
        claims_consistent_with_composition=True,  # checked separately
        net_weight_e_symbol=ext.has_e_symbol,
        country_of_origin_stated=ext.has_country_of_origin,
        no_therapeutic_claims=True,  # checked separately
        recycling_symbols_present=ext.has_recycling_symbols,
        barcode_visible=ext.has_barcode,
        qr_code_visible=ext.has_qr_code,
        species_emblem_present=ext.has_species_emblem,
        date_marking_area_present=ext.has_date_marking_area,
        translations_complete=ext.translations_complete,
        country_codes_for_languages=ext.country_codes_present,
        compliance_statement_present=ext.has_compliance_statement,
        gmo_declaration_present=ext.has_gmo_declaration,
        free_contact_for_info=ext.has_free_contact_info,
        is_raw_product=ext.is_raw_product,
        raw_warning_present=ext.has_raw_warnings,
        contains_insect_protein=ext.contains_insect_protein,
        insect_allergen_warning=ext.has_insect_allergen_warning,
        establishment_approval_number=ext.has_establishment_number,
        moisture_declaration_required=(ext.moisture or 0) > 14,
        moisture_declaration_present=ext.has_analytical_constituents,
        font_legibility_ok=ext.font_legibility_ok,
        font_legibility_notes=ext.font_legibility_notes,
        polish_language_complete=ext.polish_text_complete,
    )


def _map_confidence(text: str) -> ExtractionConfidence:
    low = text.lower().strip()
    if low in ("high", "wysoka"):
        return ExtractionConfidence.HIGH
    if low in ("medium", "średnia", "srednia"):
        return ExtractionConfidence.MEDIUM
    return ExtractionConfidence.LOW


def _check_eu_issues(eu: EULabellingCheck) -> list[Issue]:
    issues: list[Issue] = []
    checks = {
        "ingredients_listed": ("EU_NO_INGREDIENTS", "Brak listy skladnikow"),
        "analytical_constituents_present": (
            "EU_NO_ANALYTICAL", "Brak skladnikow analitycznych",
        ),
        "manufacturer_info": ("EU_NO_MANUFACTURER", "Brak danych producenta"),
        "net_weight_declared": ("EU_NO_NET_WEIGHT", "Brak masy netto"),
        "species_clearly_stated": ("EU_NO_SPECIES", "Brak okreslenia gatunku"),
        "batch_or_date_present": ("EU_NO_BATCH_DATE", "Brak nr partii i daty"),
    }
    for field_name, (code, desc) in checks.items():
        if not getattr(eu, field_name):
            issues.append(Issue(
                severity=Severity.CRITICAL,
                code=code,
                description=f"{desc} (Reg 767/2009)",
                fediaf_reference="EU Reg 767/2009",
                source="RULE",
            ))
    return issues


def _check_packaging_issues(pkg: PackagingCheck, ext: LabelExtraction) -> list[Issue]:
    issues: list[Issue] = []

    if not pkg.free_contact_for_info:
        issues.append(Issue(
            severity=Severity.WARNING,
            code="PKG_NO_CONTACT_INFO",
            description="Brak bezplatnego kontaktu do info o dodatkach (Art.19)",
            fediaf_reference="EU Reg 767/2009 Art.19",
            source="RULE",
        ))

    if not pkg.establishment_approval_number:
        issues.append(Issue(
            severity=Severity.WARNING,
            code="PKG_NO_ESTABLISHMENT_NR",
            description="Brak numeru zatwierdzenia zakladu",
            fediaf_reference="EU Reg 767/2009 + Reg 183/2005",
            source="RULE",
        ))

    if not pkg.feeding_guidelines_present:
        issues.append(Issue(
            severity=Severity.WARNING,
            code="PKG_NO_FEEDING_GUIDE",
            description="Brak instrukcji dawkowania",
            fediaf_reference="EU Reg 767/2009 Art.17(1)(f)",
            source="RULE",
        ))

    if ext.is_raw_product and not ext.has_raw_warnings:
        issues.append(Issue(
            severity=Severity.CRITICAL,
            code="PKG_RAW_NO_WARNING",
            description='Surowa karma bez ostrzezen "PET FOOD ONLY" / "NOT FOR HUMAN CONSUMPTION"',
            fediaf_reference="EU Reg 142/2011 Annex XIII",
            source="RULE",
        ))

    if pkg.moisture_declaration_required and not pkg.moisture_declaration_present:
        issues.append(Issue(
            severity=Severity.WARNING,
            code="PKG_MOISTURE_NOT_DECLARED",
            description="Wilgotnosc >14% — deklaracja obowiazkowa",
            fediaf_reference="EU Reg 767/2009 Annex V",
            source="RULE",
        ))

    if pkg.product_classification == ProductClassification.NOT_STATED:
        issues.append(Issue(
            severity=Severity.WARNING,
            code="PKG_NO_CLASSIFICATION",
            description="Brak klasyfikacji: pelnoporcjowa/uzupelniajaca/przysmak",
            fediaf_reference="EU Reg 767/2009",
            source="RULE",
        ))

    return issues


def _check_claims(ext: LabelExtraction) -> list[Issue]:
    """Check claims against ingredients for consistency."""
    issues: list[Issue] = []
    ingredients_lower = {ing.lower() for ing in ext.ingredients}

    for claim in ext.claims:
        claim_lower = claim.lower()

        # "grain-free" / "bez zbóż" check
        if any(kw in claim_lower for kw in ("bez zb", "grain-free", "grain free", "getreide")):
            found_grains = _GRAIN_KEYWORDS & ingredients_lower
            if found_grains:
                issues.append(Issue(
                    severity=Severity.CRITICAL,
                    code="CLAIM_GRAIN_FREE_VIOLATED",
                    description=(
                        f'Claim "{claim}" ale w skladzie: '
                        f'{", ".join(found_grains)}'
                    ),
                    source="RULE",
                ))

        # Therapeutic-sounding claims
        therapeutic_kw = [
            "leczy", "zapobiega", "cure", "prevent", "treat disease",
            "leczniczy", "therapeutic",
        ]
        if any(kw in claim_lower for kw in therapeutic_kw):
            issues.append(Issue(
                severity=Severity.CRITICAL,
                code="CLAIM_THERAPEUTIC",
                description=f'Claim leczniczy: "{claim}" (naruszenie Art.13)',
                fediaf_reference="EU Reg 767/2009 Art.13",
                source="RULE",
            ))

    return issues


def _determine_status(score: int) -> ComplianceStatus:
    if score >= 70:
        return ComplianceStatus.COMPLIANT
    if score >= 50:
        return ComplianceStatus.REQUIRES_REVIEW
    return ComplianceStatus.NON_COMPLIANT


def _generate_recommendations(issues: list[Issue]) -> list[str]:
    """Generate actionable recommendations from issue list."""
    recs: list[str] = []
    codes_seen: set[str] = set()

    for issue in issues:
        if issue.code in codes_seen:
            continue
        codes_seen.add(issue.code)

        if issue.code.endswith("_BELOW_MIN"):
            nutrient = issue.code.replace("_BELOW_MIN", "").replace("_", " ").lower()
            recs.append(
                f"Zwieksz zawartosc {nutrient} do minimum FEDIAF."
            )
        elif issue.code.endswith("_ABOVE_MAX"):
            nutrient = issue.code.replace("_ABOVE_MAX", "").replace("_", " ").lower()
            recs.append(
                f"Zmniejsz zawartosc {nutrient} do maksimum FEDIAF."
            )
        elif issue.code.startswith("EU_NO_"):
            recs.append(f"Dodaj brakujacy element: {issue.description}")
        elif issue.code.startswith("PKG_"):
            recs.append(issue.description)
        elif issue.code.startswith("CLAIM_"):
            recs.append(f"Skoryguj claim: {issue.description}")

    return recs
