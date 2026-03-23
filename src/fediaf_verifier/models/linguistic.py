"""Linguistic verification models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class LinguisticIssue(NullSafeBase):
    """A single linguistic issue found on the label."""

    issue_type: str = Field(
        default="spelling",
        description="spelling/grammar/punctuation/diacritics/terminology",
    )
    original: str = ""
    suggestion: str = ""
    context: str = ""
    explanation: str = ""
    confidence: str = Field(
        default="medium",
        description="'high' (AI+Hunspell agree), 'medium' (AI only), 'low' (AI only, Hunspell disagrees)",
    )
    verified_by: str = Field(
        default="ai_only",
        description="Verification source: 'ai+hunspell', 'ai_only', 'hunspell_only'",
    )


class LinguisticReport(NullSafeBase):
    """AI output for linguistic verification."""

    detected_language: str = ""
    detected_language_name: str = ""
    issues: list[LinguisticIssue] = Field(default_factory=list)
    overall_quality: str = ""  # "excellent" / "good" / "needs_review" / "poor"
    summary: str = ""


class LinguisticCheckResult(NullSafeBase):
    """Internal pipeline result wrapping LinguisticReport + error handling."""

    performed: bool = False
    report: LinguisticReport | None = None
    error: str | None = None
