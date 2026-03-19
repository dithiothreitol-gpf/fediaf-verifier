"""Translation verification models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class TranslatedSection(NullSafeBase):
    """A single translated section of the label."""

    section_name: str = Field(
        default="", description="e.g. 'Composition', 'Analytical constituents'"
    )
    original_text: str = Field(
        default="", description="Text as found on the label or pasted"
    )
    translated_text: str = Field(
        default="", description="Translation to target language"
    )
    notes: str = Field(
        default="",
        description="Translator notes (ambiguity, alternatives, terminology)",
    )


class TranslationReport(NullSafeBase):
    """AI output for label translation."""

    source_language: str = Field(default="", description="Detected, e.g. 'pl'")
    source_language_name: str = Field(default="", description="e.g. 'polski'")
    target_language: str = Field(default="", description="User-selected, e.g. 'en'")
    target_language_name: str = Field(default="", description="e.g. 'English'")
    sections: list[TranslatedSection] = Field(default_factory=list)
    overall_notes: str = Field(default="", description="General observations")
    summary: str = Field(default="", description="Brief summary")


class TranslationResult(NullSafeBase):
    """Pipeline result wrapping TranslationReport + error handling."""

    performed: bool = False
    report: TranslationReport | None = None
    error: str | None = None
