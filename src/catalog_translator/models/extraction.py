"""PDF extraction models."""

from __future__ import annotations

from pydantic import Field

from fediaf_verifier.models.base import NullSafeBase


class TextBlock(NullSafeBase):
    """Single text block extracted from a PDF page."""

    text: str = ""
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    block_index: int = 0


class PageExtraction(NullSafeBase):
    """All text blocks from a single PDF page."""

    page_number: int = 0
    blocks: list[TextBlock] = Field(default_factory=list)
    width: float = 0.0
    height: float = 0.0


class CatalogExtraction(NullSafeBase):
    """Full extraction result for a PDF catalog."""

    pages: list[PageExtraction] = Field(default_factory=list)
    total_pages: int = 0
    source_filename: str = ""
