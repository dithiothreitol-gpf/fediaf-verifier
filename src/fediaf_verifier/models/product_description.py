"""Product description generation models for e-commerce and marketing."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class ProductDescriptionSection(NullSafeBase):
    """A single section of the generated product description."""

    section_name: str = Field(
        default="",
        description="Internal key, e.g. 'headline', 'key_benefits', 'ingredient_story'",
    )
    section_title: str = Field(
        default="",
        description="Display title in target language",
    )
    content: str = Field(
        default="", description="Plain text content of the section"
    )
    html_content: str = Field(
        default="", description="HTML-formatted content for e-commerce use"
    )


class SEOMetadata(NullSafeBase):
    """SEO metadata for the product description."""

    meta_title: str = Field(
        default="", description="SEO title, max 60 characters"
    )
    meta_description: str = Field(
        default="", description="SEO meta description, max 160 characters"
    )
    keywords: list[str] = Field(
        default_factory=list, description="5-10 SEO keywords"
    )
    focus_keyword: str = Field(
        default="", description="Primary keyword for SEO"
    )


class ClaimWarning(NullSafeBase):
    """Warning about a marketing claim used in the description."""

    claim_text: str = Field(default="", description="The claim in question")
    warning_type: str = Field(
        default="",
        description=(
            "'forbidden_therapeutic', 'unsubstantiated', "
            "'naming_rule_violation', 'needs_evidence'"
        ),
    )
    explanation: str = Field(
        default="", description="Why this claim is problematic"
    )
    recommendation: str = Field(
        default="", description="Suggested alternative or action"
    )


class ProductDescriptionReport(NullSafeBase):
    """AI output for product description generation."""

    product_name: str = Field(default="", description="Product name")
    species: str = Field(default="", description="Target species")
    lifestage: str = Field(default="", description="Target lifestage")
    food_type: str = Field(default="", description="Food type")
    language: str = Field(default="", description="ISO 639-1 code")
    language_name: str = Field(default="", description="Full language name")
    tone: str = Field(
        default="standard",
        description="'premium', 'scientific', 'natural', 'standard'",
    )

    headline: str = Field(
        default="", description="1-sentence compelling product positioning"
    )
    short_description: str = Field(
        default="", description="2-3 sentences for product cards/listings"
    )
    bullet_points: list[str] = Field(
        default_factory=list, description="5-7 key selling points"
    )

    sections: list[ProductDescriptionSection] = Field(default_factory=list)
    seo: SEOMetadata | None = None

    claims_used: list[str] = Field(
        default_factory=list,
        description="Marketing claims included in the description",
    )
    claims_warnings: list[ClaimWarning] = Field(
        default_factory=list,
        description="Compliance warnings about claims",
    )

    complete_html: str = Field(
        default="",
        description="All sections combined as HTML",
    )
    complete_text: str = Field(
        default="",
        description="All sections combined as plain text",
    )
    summary: str = Field(
        default="", description="Brief summary of generated description"
    )


class ProductDescriptionResult(NullSafeBase):
    """Pipeline result wrapping ProductDescriptionReport + error handling."""

    performed: bool = False
    report: ProductDescriptionReport | None = None
    error: str | None = None
