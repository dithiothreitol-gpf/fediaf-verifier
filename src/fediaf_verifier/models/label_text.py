"""Label text generation models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class LabelTextSection(NullSafeBase):
    """A single section of generated label text."""

    section_name: str = Field(
        default="",
        description="Internal key, e.g. 'composition', 'analytical_constituents'",
    )
    section_title: str = Field(
        default="",
        description="Display title in target language, e.g. 'Analytical constituents'",
    )
    content: str = Field(
        default="", description="Full section text in target language"
    )
    regulatory_reference: str = Field(
        default="",
        description="EU regulation reference, e.g. 'EU 767/2009 Art.17'",
    )
    notes: str = Field(
        default="",
        description="Additional notes or explanations for this section",
    )


class FeedingGuideline(NullSafeBase):
    """A single row of the feeding guidelines table."""

    weight_range: str = Field(
        default="",
        description="Animal weight range, e.g. '2-5 kg'",
    )
    daily_amount: str = Field(
        default="",
        description="Recommended daily amount, e.g. '40-80 g'",
    )


class LabelTextReport(NullSafeBase):
    """AI output for label text generation."""

    product_name: str = Field(default="", description="Product name used in text")
    species: str = Field(default="", description="Target species, e.g. 'dog'")
    lifestage: str = Field(default="", description="Target lifestage, e.g. 'adult'")
    food_type: str = Field(default="", description="Food type, e.g. 'dry'")
    language: str = Field(default="", description="ISO 639-1 code, e.g. 'en'")
    language_name: str = Field(
        default="", description="Full language name, e.g. 'English'"
    )
    sections: list[LabelTextSection] = Field(default_factory=list)
    feeding_table: list[FeedingGuideline] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    complete_text: str = Field(
        default="",
        description="All sections combined into final label text",
    )
    summary: str = Field(default="", description="Brief summary of generated text")


class LabelTextResult(NullSafeBase):
    """Pipeline result wrapping LabelTextReport + error handling."""

    performed: bool = False
    report: LabelTextReport | None = None
    error: str | None = None
