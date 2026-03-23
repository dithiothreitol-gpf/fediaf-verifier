"""Pydantic v2 models for FEDIAF verifier."""

from .claims_check import (
    ClaimValidation,
    ClaimsCheckReport,
    ClaimsCheckResult,
    NamingRuleCheck,
)
from .cross_check import CrossCheckResult, Discrepancy
from .design_analysis import (
    CompetitiveBenchmark,
    DesignAnalysisReport,
    DesignAnalysisResult,
    DesignCategoryScore,
    DesignIssue,
)
from .ean_check import EANCheckReport, EANCheckResult, EANResult, QRCodeResult
from .eu_labelling import EULabellingCheck
from .label_diff import (
    DiffChange,
    DiffLayoutChange,
    LabelDiffReport,
    LabelDiffResult,
    NewIssue,
)
from .extraction import LabelExtraction, SecondaryCheck
from .issues import Issue, Severity
from .label_text import (
    FeedingGuideline,
    LabelTextReport,
    LabelTextResult,
    LabelTextSection,
)
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
    LinguisticReport,
)
from .market_check import MarketCheckReport, MarketCheckResult, MarketRequirement
from .market_trends import MarketTrends, Positioning
from .translation import TranslatedSection, TranslationReport, TranslationResult
from .nutrients import NUTRIENT_FIELDS, NutrientsOnly, NutrientValues
from .packaging import PackagingCheck, ProductClassification
from .product_description import (
    ClaimWarning,
    ProductDescriptionReport,
    ProductDescriptionResult,
    ProductDescriptionSection,
    SEOMetadata,
)
from .product import FoodType, Lifestage, Product, Species
from .report import (
    ComplianceStatus,
    EnrichedReport,
    ExtractionConfidence,
    VerificationReport,
)

__all__ = [
    "NUTRIENT_FIELDS",
    "ClaimValidation",
    "ClaimWarning",
    "ClaimsCheckReport",
    "ClaimsCheckResult",
    "CompetitiveBenchmark",
    "ComplianceStatus",
    "CrossCheckResult",
    "DesignAnalysisReport",
    "DesignAnalysisResult",
    "DesignCategoryScore",
    "DesignIssue",
    "DiffChange",
    "DiffLayoutChange",
    "Discrepancy",
    "EANCheckReport",
    "EANCheckResult",
    "EANResult",
    "EULabellingCheck",
    "NewIssue",
    "EnrichedReport",
    "ExtractionConfidence",
    "FeedingGuideline",
    "FoodType",
    "GlyphIssue",
    "Issue",
    "LabelDiffReport",
    "LabelDiffResult",
    "LabelExtraction",
    "LabelStructureCheckResult",
    "LabelTextReport",
    "LabelTextResult",
    "LabelTextSection",
    "LabelStructureReport",
    "LanguageSectionInfo",
    "Lifestage",
    "LinguisticCheckResult",
    "LinguisticIssue",
    "LinguisticReport",
    "MarketCheckReport",
    "MarketCheckResult",
    "MarketRequirement",
    "MarketTrends",
    "NamingRuleCheck",
    "NutrientValues",
    "NutrientsOnly",
    "PackagingCheck",
    "Positioning",
    "Product",
    "ProductDescriptionReport",
    "ProductDescriptionResult",
    "ProductDescriptionSection",
    "ProductClassification",
    "QRCodeResult",
    "SEOMetadata",
    "SecondaryCheck",
    "Severity",
    "Species",
    "StructureIssue",
    "TranslatedSection",
    "TranslationReport",
    "TranslationResult",
    "VerificationReport",
]
