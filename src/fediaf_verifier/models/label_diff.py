"""Label version comparison (diff) models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class DiffChange(NullSafeBase):
    """A single text change between label versions."""

    section: str = Field(
        default="",
        description="e.g. 'ingredients', 'analytical_constituents', 'claims'",
    )
    change_type: str = Field(
        default="modified",
        description="'added', 'removed', 'modified', 'moved'",
    )
    old_text: str = ""
    new_text: str = ""
    severity: str = Field(default="info", description="'critical', 'warning', 'info'")
    regulatory_impact: str = ""


class DiffLayoutChange(NullSafeBase):
    """A layout/visual change between versions."""

    description: str = ""
    area: str = ""
    severity: str = Field(default="info", description="'critical', 'warning', 'info'")


class NewIssue(NullSafeBase):
    """A new problem introduced by changes."""

    description: str = ""
    severity: str = Field(default="warning")
    introduced_by_change: str = Field(
        default="", description="Which change caused this"
    )


class LabelDiffReport(NullSafeBase):
    """AI output for label version comparison."""

    old_label_summary: str = ""
    new_label_summary: str = ""
    text_changes: list[DiffChange] = Field(default_factory=list)
    layout_changes: list[DiffLayoutChange] = Field(default_factory=list)
    new_issues_introduced: list[NewIssue] = Field(default_factory=list)
    issues_resolved: list[str] = Field(default_factory=list)
    overall_assessment: str = ""
    change_count: int = 0
    risk_level: str = Field(default="low", description="'low', 'medium', 'high'")
    summary: str = ""


class LabelDiffResult(NullSafeBase):
    """Pipeline result wrapping LabelDiffReport + error handling."""

    performed: bool = False
    report: LabelDiffReport | None = None
    error: str | None = None
