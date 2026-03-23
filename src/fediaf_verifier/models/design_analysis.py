"""Graphic design analysis models for label packaging evaluation."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class DesignCategoryScore(NullSafeBase):
    """Score and findings for a single design category."""

    category: str = Field(default="", description="Key, e.g. 'visual_hierarchy'")
    category_name: str = Field(
        default="", description="Display name, e.g. 'Hierarchia wizualna'"
    )
    score: int = Field(default=0, description="0-100")
    findings: list[str] = Field(
        default_factory=list, description="What was observed"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable suggestions"
    )


class DesignIssue(NullSafeBase):
    """A specific design problem found on the label."""

    category: str = Field(default="", description="Category key")
    description: str = ""
    severity: str = Field(
        default="minor",
        description="'critical', 'major', 'minor', 'suggestion'",
    )
    location: str = Field(default="", description="Area on label")
    recommendation: str = Field(default="", description="Specific fix")


class CompetitiveBenchmark(NullSafeBase):
    """How the label compares to industry standards."""

    aspect: str = Field(default="", description="What aspect")
    current_level: str = Field(
        default="", description="How the label performs"
    )
    industry_standard: str = Field(
        default="", description="What competitors typically do"
    )
    suggestion: str = Field(default="", description="What to improve")


class BenchmarkComparison(NullSafeBase):
    """Quantitative benchmark comparison for a single design category."""

    category: str = Field(default="", description="Category key")
    category_name: str = Field(default="", description="Display name")
    score: int = Field(default=0, description="Label's score for this category")
    segment: str = Field(default="", description="Product segment used for comparison")
    benchmark_low: int = Field(default=0, description="25th percentile in segment")
    benchmark_median: int = Field(default=0, description="Median in segment")
    benchmark_high: int = Field(default=0, description="75th percentile in segment")
    percentile: int = Field(
        default=0,
        description="Estimated percentile rank of this label within the segment (0–100)",
    )
    verdict: str = Field(
        default="",
        description="'below_average', 'average', 'above_average', 'excellent'",
    )


class DesignAnalysisReport(NullSafeBase):
    """AI output for graphic design analysis."""

    overall_score: int = Field(default=0, description="0-100")
    overall_assessment: str = Field(
        default="", description="1-2 sentence summary"
    )
    category_scores: list[DesignCategoryScore] = Field(default_factory=list)
    issues: list[DesignIssue] = Field(default_factory=list)
    strengths: list[str] = Field(
        default_factory=list, description="What the label does well"
    )
    competitive_benchmarks: list[CompetitiveBenchmark] = Field(
        default_factory=list,
    )
    benchmark_comparisons: list[BenchmarkComparison] = Field(
        default_factory=list,
        description="Quantitative benchmark comparisons per category against segment data",
    )
    trend_alignment: list[str] = Field(
        default_factory=list,
        description="Current industry trends observed or missed",
    )
    actionable_summary: str = Field(
        default="", description="Executive summary for R&D"
    )


class DesignAnalysisResult(NullSafeBase):
    """Pipeline result wrapping DesignAnalysisReport + error handling."""

    performed: bool = False
    report: DesignAnalysisReport | None = None
    error: str | None = None
