"""Translation unit models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from fediaf_verifier.models.base import NullSafeBase


class UnitCategory(StrEnum):
    """Content type of a translation unit."""

    HEADING = "heading"
    PRODUCT_NAME = "product_name"
    COMPOSITION = "composition"
    ANALYTICAL = "analytical_constituents"
    DESCRIPTION = "description"
    LABEL = "label"
    BADGE = "badge"
    FEEDING_GUIDE = "feeding_guide"
    OTHER = "other"


class TranslationUnit(NullSafeBase):
    """A single piece of text to be translated."""

    unit_id: str = ""
    source_text: str = ""
    category: UnitCategory = UnitCategory.OTHER
    page_number: int = 0
    section_name: str = ""
    detected_language: str = ""
    do_not_translate: bool = False
    context: str = Field(default="", description="Surrounding text for disambiguation")
