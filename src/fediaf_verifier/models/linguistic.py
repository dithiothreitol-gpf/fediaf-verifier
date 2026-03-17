"""Linguistic verification models."""

from enum import StrEnum

from pydantic import BaseModel


class LinguisticIssueType(StrEnum):
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    PUNCTUATION = "punctuation"
    DIACRITICS = "diacritics"
    TERMINOLOGY = "terminology"


class LinguisticIssue(BaseModel):
    """A single linguistic issue found on the label."""

    issue_type: LinguisticIssueType
    original: str
    suggestion: str
    context: str
    explanation: str


class LinguisticReport(BaseModel):
    """AI output for linguistic verification.

    Used with: client.messages.parse(output_format=LinguisticReport)
    """

    detected_language: str
    detected_language_name: str
    issues: list[LinguisticIssue] = []
    overall_quality: str  # "excellent" / "good" / "needs_review" / "poor"
    summary: str


class LinguisticCheckResult(BaseModel):
    """Internal pipeline result wrapping LinguisticReport + error handling."""

    performed: bool = False
    report: LinguisticReport | None = None
    error: str | None = None
