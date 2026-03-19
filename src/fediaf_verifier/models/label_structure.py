"""Label structure & font completeness verification models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


def _coerce_nulls(data: Any) -> Any:
    """Pre-validator: convert None to safe defaults for AI response robustness.

    AI models frequently return null for optional string fields even when
    the prompt asks for empty strings.  This avoids Pydantic validation
    errors without loosening the type system.
    """
    if not isinstance(data, dict):
        return data
    for key, val in list(data.items()):
        if val is None:
            # Leave bbox, missing_characters etc. as None — they are typed
            # as Optional.  Only coerce fields that are plain str/bool/list.
            continue
        if isinstance(val, list):
            data[key] = [
                _coerce_nulls(item) if isinstance(item, dict) else item
                for item in val
            ]
        elif isinstance(val, dict) and key not in ("diacritics_check",):
            data[key] = _coerce_nulls(val)
    return data


class _NullSafeBase(BaseModel):
    """BaseModel that converts None → '' for str fields before validation."""

    @model_validator(mode="before")
    @classmethod
    def _null_to_empty(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        field_types = cls.model_fields
        for key, val in list(data.items()):
            if val is None and key in field_types:
                annotation = field_types[key].annotation
                # If the field is a plain str (not Optional[str]), replace None
                if annotation is str:
                    data[key] = ""
                elif annotation is bool:
                    data[key] = False
                elif annotation is int:
                    data[key] = 0
        return data


class LanguageSectionInfo(_NullSafeBase):
    """Single language section detected on the label."""

    language_code: str = Field(description="ISO 639-1 code, e.g. 'pl', 'de'")
    language_name: str = Field(
        default="", description="Full name, e.g. 'polski', 'Deutsch'"
    )
    marker_present: bool = Field(
        default=False,
        description="Whether the language marker/emblem is visible",
    )
    marker_type: str = Field(
        default="",
        description="Type of marker: 'flag', 'code', 'text', 'icon', 'none'",
    )
    marker_text: str = Field(
        default="",
        description="Exact text/description of the marker as seen on the label",
    )
    content_present: bool = Field(
        default=True,
        description="Whether the section contains actual text content",
    )
    content_complete: bool = Field(
        default=True,
        description="Whether the section content appears complete (not truncated)",
    )
    section_elements: list[str] = Field(
        default_factory=list,
        description=(
            "Which label elements are present in this section "
            "(e.g. 'ingredients', 'analytical_constituents', 'feeding_guidelines')"
        ),
    )
    missing_elements: list[str] = Field(
        default_factory=list,
        description="Elements expected but missing in this language section",
    )
    notes: str = Field(default="", description="Additional observations")
    bbox: list[int | float] | None = Field(
        default=None,
        description="Bounding box [x, y, w, h] normalized 0-1000, or null",
    )


class GlyphIssue(_NullSafeBase):
    """A single font/glyph problem detected on the label."""

    language_code: str = Field(
        default="", description="Language section where the issue was found"
    )
    issue_type: str = Field(
        default="missing_glyph",
        description=(
            "Type: 'missing_glyph', 'substituted_glyph', 'blank_space', "
            "'tofu_box', 'wrong_diacritic', 'encoding_error'"
        ),
    )
    affected_text: str = Field(
        default="", description="The word or fragment with the issue"
    )
    expected_text: str = Field(
        default="",
        description="What the text should look like with correct glyphs",
    )
    missing_characters: list[str] = Field(
        default_factory=list,
        description="Specific characters that are missing or broken (e.g. ['ą', 'ę'])",
    )
    location: str = Field(
        default="",
        description="Where on the label (e.g. 'ingredients list', 'feeding guidelines')",
    )
    explanation: str = Field(default="")
    bbox: list[int | float] | None = Field(
        default=None,
        description="Bounding box [x, y, w, h] normalized 0-1000, or null",
    )


class StructureIssue(_NullSafeBase):
    """A structural problem with language sections layout."""

    issue_type: str = Field(
        default="missing_marker",
        description=(
            "Type: 'missing_marker', 'orphaned_text', 'section_overlap', "
            "'section_gap', 'marker_damaged', 'inconsistent_order', "
            "'missing_section', 'duplicate_marker'"
        ),
    )
    description: str = ""
    affected_languages: list[str] = Field(
        default_factory=list,
        description="Language codes affected",
    )
    severity: str = Field(
        default="warning",
        description="'critical', 'warning', 'info'",
    )
    location: str = Field(default="")
    bbox: list[int | float] | None = Field(
        default=None,
        description="Bounding box [x, y, w, h] normalized 0-1000, or null",
    )


class LabelStructureReport(_NullSafeBase):
    """AI output for label structure & font verification."""

    # Language sections found
    languages_expected: list[str] = Field(
        default_factory=list,
        description="Language codes expected based on markers/context",
    )
    language_sections: list[LanguageSectionInfo] = Field(
        default_factory=list,
    )

    # Structure issues
    structure_issues: list[StructureIssue] = Field(
        default_factory=list,
    )

    # Font/glyph issues
    glyph_issues: list[GlyphIssue] = Field(
        default_factory=list,
    )

    # Per-language expected diacritics check
    diacritics_check: dict[str, bool] = Field(
        default_factory=dict,
        description=(
            "Per language code: True if all expected diacritics are present, "
            "False if any are missing. E.g. {'pl': False, 'de': True}"
        ),
    )

    # Summary
    overall_status: str = Field(
        default="errors",
        description="'ok', 'warnings', 'errors'",
    )
    summary: str = Field(
        default="", description="Short summary in Polish"
    )
    section_count: int = Field(
        default=0,
        description="Total number of language sections detected",
    )
    font_issues_count: int = Field(
        default=0,
        description="Total number of font/glyph issues found",
    )

    @model_validator(mode="after")
    def _normalize_status(self) -> "LabelStructureReport":
        """Normalize overall_status and compute counts if AI omitted them."""
        # Normalize status value (AI might return "OK", "Errors", etc.)
        status_map = {
            "ok": "ok", "good": "ok", "pass": "ok", "passed": "ok",
            "warnings": "warnings", "warning": "warnings",
            "errors": "errors", "error": "errors", "fail": "errors",
            "failed": "errors",
        }
        self.overall_status = status_map.get(
            self.overall_status.lower().strip(), self.overall_status
        )

        # Auto-compute counts if AI returned 0 but lists are populated
        if self.section_count == 0 and self.language_sections:
            self.section_count = len(self.language_sections)
        if self.font_issues_count == 0 and self.glyph_issues:
            self.font_issues_count = len(self.glyph_issues)

        return self


class LabelStructureCheckResult(_NullSafeBase):
    """Pipeline result wrapping LabelStructureReport + error handling."""

    performed: bool = False
    report: LabelStructureReport | None = None
    error: str | None = None
