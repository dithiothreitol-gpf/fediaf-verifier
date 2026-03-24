"""Raw extraction models — what the AI sees on the label."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator

from .linguistic import LinguisticIssue


def _parse_numeric(v: Any) -> float | None:
    """Strip %-signs, whitespace, and handle comma decimals before float parsing."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip().rstrip("%").strip()
        if not v:
            return None
        v = v.replace(",", ".")
        return float(v)
    return v


FlexFloat = Annotated[float | None, BeforeValidator(_parse_numeric)]


class LabelExtraction(BaseModel):
    """Raw data extracted from label. No compliance judgments — just what's visible."""

    # Product identification (raw text, not enums)
    product_name: str | None = None
    brand: str | None = None
    species: str | None = None
    lifestage: str | None = None
    food_type_text: str | None = None
    net_weight: str | None = None

    # Nutrients (% as-fed, exactly as printed on label)
    crude_protein: float | None = None
    crude_fat: float | None = None
    crude_fibre: float | None = None
    moisture: float | None = None
    crude_ash: float | None = None
    calcium: float | None = None
    phosphorus: float | None = None

    # Ingredients (flat list, order preserved from label)
    ingredients: list[str] = []

    # Presence checks — what's on the label (bool)
    has_feeding_guidelines: bool = False
    has_storage_instructions: bool = False
    has_ingredients_list: bool = False
    has_analytical_constituents: bool = False
    has_manufacturer_info: bool = False
    has_net_weight: bool = False
    has_species_stated: bool = False
    has_batch_number: bool = False
    has_best_before_date: bool = False
    has_recycling_symbols: bool = False
    has_barcode: bool = False
    has_qr_code: bool = False
    has_species_emblem: bool = False
    has_date_marking_area: bool = False
    has_country_of_origin: bool = False
    has_e_symbol: bool = False
    has_establishment_number: bool = False
    has_free_contact_info: bool = False
    has_compliance_statement: bool = False
    has_gmo_declaration: bool = False

    # Product classification (raw text)
    product_classification_text: str | None = None

    # Claims found on label (raw text)
    claims: list[str] = []

    # Special product flags
    is_raw_product: bool = False
    has_raw_warnings: bool = False
    contains_insect_protein: bool = False
    has_insect_allergen_warning: bool = False

    # Visual quality assessment
    extraction_confidence: str = "HIGH"
    values_requiring_check: list[str] = []
    font_legibility_ok: bool = True
    font_legibility_notes: str = ""

    # Languages
    languages_detected: list[str] = []
    translations_complete: bool = True
    country_codes_present: bool = True
    polish_text_complete: bool = True


class SecondaryCheck(BaseModel):
    """Combined cross-check + linguistic verification (Call 2 output)."""

    # Cross-check: independent re-read of nutrients
    cross_crude_protein: FlexFloat = None
    cross_crude_fat: FlexFloat = None
    cross_crude_fibre: FlexFloat = None
    cross_moisture: FlexFloat = None
    cross_crude_ash: FlexFloat = None
    cross_calcium: FlexFloat = None
    cross_phosphorus: FlexFloat = None
    cross_reading_notes: str = ""

    # Linguistic verification
    detected_language: str = ""
    detected_language_name: str = ""
    linguistic_issues: list[LinguisticIssue] = []
    overall_language_quality: str = "excellent"
    language_summary: str = ""
