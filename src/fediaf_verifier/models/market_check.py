"""Per-market regulatory compliance check models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class MarketRequirement(NullSafeBase):
    """Result of checking a single market-specific requirement."""

    requirement_id: str = Field(
        default="", description="Rule ID, e.g. 'DE_LMIV_FONT'"
    )
    category: str = Field(
        default="",
        description="'language', 'labeling', 'claims', 'legal', 'packaging'",
    )
    description: str = Field(
        default="", description="What the requirement mandates"
    )
    regulation_reference: str = Field(
        default="", description="Reference to regulation, e.g. 'EU 1169/2011'"
    )
    compliant: bool = Field(
        default=False, description="Whether the label meets this requirement"
    )
    finding: str = Field(
        default="", description="What was found on the label"
    )
    recommendation: str = Field(
        default="", description="What to change for compliance"
    )
    severity: str = Field(
        default="warning",
        description="'critical', 'warning', 'info'",
    )


class MarketCheckReport(NullSafeBase):
    """AI output for per-market regulatory compliance check."""

    target_market: str = Field(
        default="", description="Full market name, e.g. 'Niemcy'"
    )
    target_market_code: str = Field(
        default="", description="ISO 3166-1 alpha-2 code, e.g. 'DE'"
    )
    base_eu_compliant: bool = Field(
        default=False,
        description="Whether label meets base EU 767/2009 requirements",
    )
    market_specific_requirements: list[MarketRequirement] = Field(
        default_factory=list,
        description="Results for each country-specific requirement",
    )
    language_requirements_met: bool = Field(
        default=False,
        description="Whether required language is present and complete",
    )
    language_notes: str = Field(
        default="", description="Details about language compliance"
    )
    additional_certifications_recommended: list[str] = Field(
        default_factory=list,
        description="Certifications the product should obtain",
    )
    overall_compliance: str = Field(
        default="issues_found",
        description="'compliant', 'issues_found', 'non_compliant'",
    )
    score: int = Field(
        default=0, description="Overall compliance score 0-100"
    )
    summary: str = Field(
        default="", description="Brief summary of findings"
    )


class MarketCheckResult(NullSafeBase):
    """Pipeline result wrapping MarketCheckReport + error handling."""

    performed: bool = False
    report: MarketCheckReport | None = None
    error: str | None = None
