"""Claims vs Composition validation models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class ClaimValidation(NullSafeBase):
    """Validation result for a single marketing claim."""

    claim_text: str = Field(default="", description="Original claim text from label")
    claim_category: str = Field(
        default="other",
        description=(
            "'percentage', 'grain_free', 'ingredient_highlight', "
            "'nutritional', 'naming_rule', 'therapeutic', 'other'"
        ),
    )
    is_consistent: bool = Field(
        default=True, description="Whether the claim is consistent with composition"
    )
    inconsistency_description: str = Field(
        default="", description="What is inconsistent (if any)"
    )
    relevant_ingredients: list[str] = Field(
        default_factory=list,
        description="Ingredients relevant to this claim",
    )
    severity: str = Field(
        default="info",
        description="'critical', 'warning', 'info'",
    )
    recommendation: str = Field(
        default="", description="Suggested corrective action"
    )


class NamingRuleCheck(NullSafeBase):
    """EU 767/2009 naming percentage rule check."""

    product_name: str = Field(default="", description="Full product name")
    trigger_word: str = Field(
        default="",
        description="Word that triggers the rule (e.g. 'z', 'bogaty w', main name)",
    )
    required_minimum_percent: float = Field(
        default=0.0,
        description="Minimum % required by the naming rule (4, 14, or 26)",
    )
    ingredient_name: str = Field(
        default="", description="Ingredient referenced in the name"
    )
    actual_percent: float | None = Field(
        default=None, description="Actual % stated on label (if available)"
    )
    compliant: bool = Field(
        default=True, description="Whether the naming rule is satisfied"
    )
    notes: str = Field(default="", description="Additional notes")


class ClaimsCheckReport(NullSafeBase):
    """AI output for claims vs composition analysis."""

    claims_found: list[str] = Field(
        default_factory=list, description="All marketing claims found on label"
    )
    ingredients_with_percentages: list[str] = Field(
        default_factory=list,
        description="Ingredients with stated percentages",
    )
    claim_validations: list[ClaimValidation] = Field(
        default_factory=list,
        description="Per-claim consistency validation results",
    )
    naming_rule_check: NamingRuleCheck | None = Field(
        default=None, description="EU 767/2009 naming % rule check"
    )
    grain_free_check_passed: bool | None = Field(
        default=None,
        description="None if no grain-free claim; True/False otherwise",
    )
    grain_ingredients_found: list[str] = Field(
        default_factory=list,
        description="Grain ingredients found (relevant if grain-free claim)",
    )
    therapeutic_claims_found: list[str] = Field(
        default_factory=list,
        description="Therapeutic/medicinal claims (forbidden per EU 767/2009 Art.13)",
    )
    overall_consistency: str = Field(
        default="consistent",
        description=(
            "'consistent', 'inconsistencies_found', 'critical_issues'"
        ),
    )
    score: int = Field(
        default=100, description="Claims consistency score 0-100"
    )
    summary: str = Field(default="", description="Summary in Polish")


class ClaimsCheckResult(NullSafeBase):
    """Pipeline result wrapping ClaimsCheckReport + error handling."""

    performed: bool = False
    report: ClaimsCheckReport | None = None
    error: str | None = None
