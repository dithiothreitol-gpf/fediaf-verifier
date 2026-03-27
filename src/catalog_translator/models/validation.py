"""Validation models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from fediaf_verifier.models.base import NullSafeBase


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(NullSafeBase):
    """Single validation finding."""

    unit_id: str = ""
    page: int = 0
    check_type: str = ""
    severity: ValidationSeverity = ValidationSeverity.WARNING
    message: str = ""
    source_text: str = ""
    translated_text: str = ""


class ValidationReport(NullSafeBase):
    """Aggregated validation results."""

    issues: list[ValidationIssue] = Field(default_factory=list)
    total_checked: int = 0
    errors_count: int = 0
    warnings_count: int = 0
