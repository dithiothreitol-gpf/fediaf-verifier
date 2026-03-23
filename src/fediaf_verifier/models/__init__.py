"""Pydantic v2 models for FEDIAF verifier."""

from .artwork_inspection import (
    ArtworkInspectionReport,
    ArtworkInspectionResult,
    AttentionRegion,
    ColorAnalysisReport,
    ColorComparison,
    DominantColor,
    ICCProfileInfo,
    OCRComparisonReport,
    OCRTextBlock,
    PixelDiffRegion,
    PixelDiffReport,
    PrintIssue,
    PrintReadinessReport,
    SaliencyReport,
    SaliencyResult,
    TextDiffChange,
)
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
from .presentation_check import (
    BrandComplianceCheck,
    NameConsistencyCheck,
    NamingConventionCheck,
    PresentationCheckReport,
    PresentationCheckResult,
    RecipeClaimCheck,
    TrademarkCheck,
)
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
    "ArtworkInspectionReport",
    "ArtworkInspectionResult",
    "BrandComplianceCheck",
    "ClaimValidation",
    "ClaimWarning",
    "ClaimsCheckReport",
    "ClaimsCheckResult",
    "ColorAnalysisReport",
    "ColorComparison",
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
    "DominantColor",
    "EANCheckReport",
    "EANCheckResult",
    "EANResult",
    "EULabellingCheck",
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
    "LabelStructureReport",
    "LabelTextReport",
    "LabelTextResult",
    "LabelTextSection",
    "LanguageSectionInfo",
    "Lifestage",
    "LinguisticCheckResult",
    "LinguisticIssue",
    "LinguisticReport",
    "MarketCheckReport",
    "MarketCheckResult",
    "MarketRequirement",
    "MarketTrends",
    "NUTRIENT_FIELDS",
    "NameConsistencyCheck",
    "NamingConventionCheck",
    "NamingRuleCheck",
    "NewIssue",
    "NutrientValues",
    "NutrientsOnly",
    "PackagingCheck",
    "PixelDiffRegion",
    "PixelDiffReport",
    "Positioning",
    "PresentationCheckReport",
    "PresentationCheckResult",
    "Product",
    "ProductClassification",
    "ProductDescriptionReport",
    "ProductDescriptionResult",
    "ProductDescriptionSection",
    "PrintIssue",
    "PrintReadinessReport",
    "QRCodeResult",
    "RecipeClaimCheck",
    "SEOMetadata",
    "SecondaryCheck",
    "Severity",
    "Species",
    "StructureIssue",
    "TrademarkCheck",
    "TranslatedSection",
    "TranslationReport",
    "TranslationResult",
    "VerificationReport",
]
