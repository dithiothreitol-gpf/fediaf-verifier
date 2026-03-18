"""Pydantic v2 models for FEDIAF verifier."""

from .cross_check import CrossCheckResult, Discrepancy
from .eu_labelling import EULabellingCheck
from .extraction import LabelExtraction, SecondaryCheck
from .issues import Issue, Severity
from .linguistic import (
    LinguisticCheckResult,
    LinguisticIssue,
    LinguisticIssueType,
    LinguisticReport,
)
from .market_trends import MarketTrends, Positioning
from .nutrients import NUTRIENT_FIELDS, NutrientsOnly, NutrientValues
from .packaging import PackagingCheck, ProductClassification
from .product import FoodType, Lifestage, Product, Species
from .report import (
    ComplianceStatus,
    EnrichedReport,
    ExtractionConfidence,
    VerificationReport,
)

__all__ = [
    "NUTRIENT_FIELDS",
    "ComplianceStatus",
    "CrossCheckResult",
    "Discrepancy",
    "EULabellingCheck",
    "EnrichedReport",
    "ExtractionConfidence",
    "FoodType",
    "Issue",
    "LabelExtraction",
    "Lifestage",
    "LinguisticCheckResult",
    "LinguisticIssue",
    "LinguisticIssueType",
    "LinguisticReport",
    "MarketTrends",
    "NutrientValues",
    "NutrientsOnly",
    "PackagingCheck",
    "Positioning",
    "Product",
    "ProductClassification",
    "SecondaryCheck",
    "Severity",
    "Species",
    "VerificationReport",
]
