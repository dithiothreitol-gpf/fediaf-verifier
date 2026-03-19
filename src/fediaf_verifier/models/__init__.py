"""Pydantic v2 models for FEDIAF verifier."""

from .cross_check import CrossCheckResult, Discrepancy
from .design_analysis import (
    CompetitiveBenchmark,
    DesignAnalysisReport,
    DesignAnalysisResult,
    DesignCategoryScore,
    DesignIssue,
)
from .eu_labelling import EULabellingCheck
from .extraction import LabelExtraction, SecondaryCheck
from .issues import Issue, Severity
from .label_structure import (
    GlyphIssue,
    LabelStructureCheckResult,
    LabelStructureReport,
    LanguageSectionInfo,
    StructureIssue,
)
from .linguistic import (
    LinguisticCheckResult,
    LinguisticIssue,
    LinguisticIssueType,
    LinguisticReport,
)
from .market_trends import MarketTrends, Positioning
from .translation import TranslatedSection, TranslationReport, TranslationResult
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
    "CompetitiveBenchmark",
    "ComplianceStatus",
    "CrossCheckResult",
    "DesignAnalysisReport",
    "DesignAnalysisResult",
    "DesignCategoryScore",
    "DesignIssue",
    "Discrepancy",
    "EULabellingCheck",
    "EnrichedReport",
    "ExtractionConfidence",
    "FoodType",
    "GlyphIssue",
    "Issue",
    "LabelExtraction",
    "LabelStructureCheckResult",
    "LabelStructureReport",
    "LanguageSectionInfo",
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
    "StructureIssue",
    "TranslatedSection",
    "TranslationReport",
    "TranslationResult",
    "VerificationReport",
]
