"""Packaging compliance check models — beyond FEDIAF/EU basics."""

from enum import StrEnum

from pydantic import BaseModel


class ProductClassification(StrEnum):
    COMPLETE = "complete"
    COMPLEMENTARY = "complementary"
    TREAT = "treat"
    NOT_STATED = "not_stated"


class PackagingCheck(BaseModel):
    """Extended packaging compliance checklist.

    Covers checks from BULT internal QA checklist + EU industry best practices.
    All fields have safe defaults so missing AI output won't break the pipeline.
    """

    # Feeding & storage (Checklist §4)
    feeding_guidelines_present: bool = False
    storage_instructions_present: bool = False

    # Product classification (§6)
    product_classification: ProductClassification = ProductClassification.NOT_STATED

    # Claims vs composition (§5) — critical for regulatory compliance
    claims_consistent_with_composition: bool = True
    claims_inconsistencies: list[str] = []
    meat_percentage_claim_consistent: bool = True

    # Legal markings (§6)
    net_weight_e_symbol: bool = False
    country_of_origin_stated: bool = False
    no_therapeutic_claims: bool = True

    # Naming percentage rule (EU Reg 767/2009 Art.17)
    naming_percentage_rule_ok: bool = True
    naming_percentage_notes: str = ""

    # Package markings (§5, §8, §13)
    recycling_symbols_present: bool = False
    barcode_visible: bool = False
    qr_code_visible: bool = False
    species_emblem_present: bool = False
    date_marking_area_present: bool = False

    # Translations & country codes (§15, §5)
    translations_complete: bool = True
    country_codes_for_languages: bool = True

    # Compliance statement
    compliance_statement_present: bool = False

    # GMO declaration (Reg 1829/2003, 1830/2003)
    gmo_declaration_required: bool = False
    gmo_declaration_present: bool = True
    gmo_notes: str = ""

    # Free contact line for additive/ingredient info (767/2009 Art.19)
    free_contact_for_info: bool = False

    # Raw/BARF warnings (Reg 142/2011 Annex XIII)
    is_raw_product: bool = False
    raw_warning_present: bool = True

    # Insect protein allergen cross-reactivity (EFSA guidance)
    contains_insect_protein: bool = False
    insect_allergen_warning: bool = True

    # Irradiation declaration (Directive 1999/2/EC)
    irradiation_declared_if_applicable: bool = True

    # Establishment approval number (767/2009 + 183/2005)
    establishment_approval_number: bool = False

    # Moisture declaration mandatory if >14% (767/2009 Annex V)
    moisture_declaration_required: bool = False
    moisture_declaration_present: bool = True

    # Font legibility (767/2009 Art.14 — min 1.2mm x-height)
    font_legibility_ok: bool = True
    font_legibility_notes: str = ""

    # Polish market — all mandatory info in Polish
    polish_language_complete: bool = True

    # Additional notes
    packaging_notes: list[str] = []
