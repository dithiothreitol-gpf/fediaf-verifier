"""Verification report models — AI output and enriched pipeline output."""

from enum import StrEnum

from pydantic import BaseModel, Field

from .cross_check import CrossCheckResult
from .eu_labelling import EULabellingCheck
from .issues import Issue
from .linguistic import LinguisticCheckResult
from .market_trends import MarketTrends
from .nutrients import NutrientValues
from .packaging import PackagingCheck
from .product import Product


class ExtractionConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ComplianceStatus(StrEnum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class VerificationReport(BaseModel):
    """Main structured output from the AI verification call.

    Used with: client.messages.parse(output_format=VerificationReport)
    """

    product: Product
    extracted_nutrients: NutrientValues
    ingredients_list: list[str] = []
    extraction_confidence: ExtractionConfidence
    values_requiring_manual_check: list[str] = []
    compliance_score: int = Field(ge=0, le=100)
    status: ComplianceStatus
    issues: list[Issue] = []
    eu_labelling_check: EULabellingCheck
    packaging_check: PackagingCheck = PackagingCheck()
    recommendations: list[str] = []
    market_trends: MarketTrends | None = None


class EnrichedReport(BaseModel):
    """Full report after all 5 reliability layers have been applied.

    Extends AI output with cross-check, hard rules, and human-review flags.
    This is what the UI renders and what gets exported.
    """

    # From VerificationReport (AI output)
    product: Product
    extracted_nutrients: NutrientValues
    ingredients_list: list[str] = []
    extraction_confidence: ExtractionConfidence
    values_requiring_manual_check: list[str] = []
    compliance_score: int = Field(ge=0, le=100)
    status: ComplianceStatus
    issues: list[Issue] = []
    eu_labelling_check: EULabellingCheck
    packaging_check: PackagingCheck = PackagingCheck()
    recommendations: list[str] = []
    market_trends: MarketTrends | None = None

    # Added by pipeline
    hard_rule_flags: list[Issue] = []
    cross_check_result: CrossCheckResult = CrossCheckResult()
    linguistic_check_result: LinguisticCheckResult = LinguisticCheckResult()
    reliability_flags: list[str] = []
    requires_human_review: bool = False
