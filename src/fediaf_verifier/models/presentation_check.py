"""Commercial presentation compliance models (recipes, names, brand, trademarks)."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


# -- Section 1: Receptury (Recipes) --------------------------------------------


class RecipeClaimCheck(NullSafeBase):
    """Validation of a single recipe-level claim."""

    claim_text: str = Field(default="", description="Original recipe claim from label")
    claim_type: str = Field(
        default="other",
        description=(
            "'original_recipe', 'vet_developed', 'single_protein', "
            "'complete_vs_complementary', 'no_artificial', "
            "'fresh_meat_percentage', 'other'"
        ),
    )
    compliant: bool = Field(
        default=True, description="Whether claim is legally substantiated"
    )
    regulation_reference: str = Field(
        default="", description="Applicable regulation (e.g. 'EU 767/2009 Art.13')"
    )
    finding: str = Field(default="", description="What was found on the label")
    issue_description: str = Field(
        default="", description="Why it's non-compliant (if any)"
    )
    recommendation: str = Field(
        default="", description="Suggested corrective action"
    )
    severity: str = Field(
        default="info", description="'critical', 'warning', 'info'"
    )


# -- Section 2: Nazwy (Names) -------------------------------------------------


class NamingConventionCheck(NullSafeBase):
    """EU 767/2009 Art.17 comprehensive naming rule check for one ingredient."""

    product_name: str = Field(default="", description="Full product name as on label")
    highlighted_ingredient: str = Field(
        default="", description="Ingredient referenced in name"
    )
    trigger_expression: str = Field(
        default="",
        description=(
            "Expression triggering the rule "
            "(e.g. 'z', 'bogaty w', main name, 'smak')"
        ),
    )
    applicable_rule: str = Field(
        default="",
        description="'100_pct', '26_pct', '14_pct', '4_pct', 'flavour', 'none'",
    )
    required_minimum_percent: float = Field(
        default=0.0, description="Minimum % required by the naming rule"
    )
    actual_percent: float | None = Field(
        default=None, description="Actual % stated on label (if available)"
    )
    compliant: bool = Field(
        default=True, description="Whether the naming rule is satisfied"
    )
    notes: str = Field(default="", description="Additional notes")


class NameConsistencyCheck(NullSafeBase):
    """Product name vs product attributes consistency."""

    check_type: str = Field(
        default="",
        description=(
            "'name_vs_food_type', 'name_vs_species', 'name_vs_lifestage', "
            "'misleading_descriptor', 'multilang_consistency'"
        ),
    )
    description: str = Field(default="", description="What was checked")
    finding: str = Field(default="", description="What was found")
    compliant: bool = Field(default=True, description="Whether consistent")
    issue_description: str = Field(
        default="", description="Problem description if non-compliant"
    )
    recommendation: str = Field(default="", description="Suggested fix")
    severity: str = Field(
        default="info", description="'critical', 'warning', 'info'"
    )


# -- Section 3: Marka (Brand) -------------------------------------------------


class BrandComplianceCheck(NullSafeBase):
    """Regulatory compliance of brand name elements."""

    brand_name: str = Field(default="", description="Full brand name as on label")
    flagged_element: str = Field(
        default="", description="Specific word/phrase triggering the check"
    )
    check_type: str = Field(
        default="",
        description=(
            "'bio_organic', 'vet_veterinary', 'natural', "
            "'medical_forbidden', 'country_origin', 'holistic', "
            "'human_grade', 'breed_specific', 'other'"
        ),
    )
    regulation_reference: str = Field(
        default="", description="Applicable regulation"
    )
    compliant: bool = Field(
        default=True,
        description="Whether brand element is legally compliant",
    )
    issue_description: str = Field(default="", description="Problem description")
    recommendation: str = Field(
        default="", description="Suggested corrective action"
    )
    severity: str = Field(
        default="info", description="'critical', 'warning', 'info'"
    )


# -- Section 4: Zastrzezenia (Trademarks / IP) --------------------------------


class TrademarkCheck(NullSafeBase):
    """Trademark / intellectual-property risk assessment for a label element."""

    element_text: str = Field(
        default="", description="Text element being checked"
    )
    element_type: str = Field(
        default="other",
        description=(
            "'product_name', 'recipe_name', 'ingredient_brand', "
            "'symbol_usage', 'other'"
        ),
    )
    potential_owner: str = Field(
        default="",
        description="Known or suspected trademark owner (if any)",
    )
    trademark_symbol_found: str = Field(
        default="",
        description="Trademark symbol found on label: 'registered', 'tm', 'none'",
    )
    risk_level: str = Field(
        default="none",
        description="'high', 'medium', 'low', 'none'",
    )
    issue_description: str = Field(default="", description="Risk description")
    recommendation: str = Field(
        default="", description="Suggested corrective action"
    )
    severity: str = Field(
        default="info", description="'critical', 'warning', 'info'"
    )


# -- Top-level report ---------------------------------------------------------


class PresentationCheckReport(NullSafeBase):
    """AI output for commercial presentation compliance analysis."""

    # Extracted context
    product_name: str = Field(default="", description="Product name as on label")
    brand_name: str = Field(default="", description="Brand name as on label")
    product_classification: str = Field(
        default="",
        description="Complete/Complementary as stated on label",
    )
    food_type: str = Field(
        default="", description="Dry/Wet/Semi-moist as on label"
    )
    species: str = Field(default="", description="Target species as on label")
    lifestage: str = Field(default="", description="Target lifestage as on label")
    ingredients_with_percentages: list[str] = Field(
        default_factory=list,
        description="Ingredients with stated percentages",
    )
    additives_list: list[str] = Field(
        default_factory=list,
        description="Additives / technological additives found",
    )

    # Section 1: Recipes
    recipe_claims_found: list[str] = Field(
        default_factory=list, description="All recipe-level claims found"
    )
    recipe_claim_checks: list[RecipeClaimCheck] = Field(
        default_factory=list,
        description="Per-claim recipe validation results",
    )
    recipe_section_score: int = Field(
        default=100, description="Recipe section score 0-100"
    )

    # Section 2: Names
    naming_convention_checks: list[NamingConventionCheck] = Field(
        default_factory=list,
        description="EU 767/2009 Art.17 naming rule checks",
    )
    name_consistency_checks: list[NameConsistencyCheck] = Field(
        default_factory=list,
        description="Name vs product attributes consistency checks",
    )
    naming_section_score: int = Field(
        default=100, description="Naming section score 0-100"
    )

    # Section 3: Brand
    brand_compliance_checks: list[BrandComplianceCheck] = Field(
        default_factory=list,
        description="Brand name regulatory compliance checks",
    )
    brand_section_score: int = Field(
        default=100, description="Brand section score 0-100"
    )

    # Section 4: Trademarks
    trademark_checks: list[TrademarkCheck] = Field(
        default_factory=list,
        description="Trademark / IP risk assessments",
    )
    trademark_section_score: int = Field(
        default=100, description="Trademark section score 0-100"
    )

    # Overall
    overall_compliance: str = Field(
        default="compliant",
        description="'compliant', 'issues_found', 'critical_issues'",
    )
    score: int = Field(
        default=100, description="Overall presentation compliance score 0-100"
    )
    summary: str = Field(default="", description="Summary in Polish")


class PresentationCheckResult(NullSafeBase):
    """Pipeline result wrapping PresentationCheckReport + error handling."""

    performed: bool = False
    report: PresentationCheckReport | None = None
    error: str | None = None
