"""Design element models — colors, text blocks, graphic regions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fediaf_verifier.models.base import NullSafeBase

from .package_spec import PackageSpec


class ColorSwatch(BaseModel):
    """A color extracted from the concept, ready for CMYK print."""

    name: str = Field(description="Descriptive name, e.g. 'Primary Blue'")
    hex: str = Field(description="Hex RGB value, e.g. '#2A5CAA'")
    cyan: float = Field(default=0, ge=0, le=100)
    magenta: float = Field(default=0, ge=0, le=100)
    yellow: float = Field(default=0, ge=0, le=100)
    key: float = Field(default=0, ge=0, le=100)
    role: str = Field(
        default="accent",
        description="Role: primary, secondary, accent, text, background",
    )

    @property
    def cmyk_tuple(self) -> tuple[float, float, float, float]:
        return (self.cyan, self.magenta, self.yellow, self.key)


class TextBlock(NullSafeBase):
    """A text element detected on the packaging concept."""

    content: str = Field(description="Text content")
    bbox: list[float] = Field(
        description="Bounding box [x, y, w, h] normalized 0-1000",
    )
    font_style: str = Field(
        default="sans_regular",
        description="Font style hint: serif_bold, sans_regular, display, etc.",
    )
    font_size_pt: float | None = Field(
        default=None,
        description="Estimated font size in points",
    )
    role: str = Field(
        default="body",
        description="Role: product_name, tagline, ingredients, weight, brand, legal, other",
    )


class GraphicRegion(NullSafeBase):
    """A graphic element detected on the packaging concept."""

    description: str = Field(description="What this element depicts")
    bbox: list[float] = Field(description="Bounding box [x, y, w, h] normalized 0-1000")
    region_type: str = Field(
        default="other",
        description="Type: logo, product_photo, pattern, icon, illustration, background",
    )


class DesignAnalysis(NullSafeBase):
    """Complete analysis of a packaging concept image."""

    package_spec: PackageSpec
    text_blocks: list[TextBlock] = Field(default_factory=list)
    graphic_regions: list[GraphicRegion] = Field(default_factory=list)
    color_swatches: list[ColorSwatch] = Field(default_factory=list)
    existing_elements: list[str] = Field(
        default_factory=list,
        description="Elements already present: 'ean_barcode', 'recycling_symbol', etc.",
    )
    typography_style: str = Field(
        default="modern_sans",
        description="Overall typography style: modern_sans, classic_serif, display, handwritten",
    )
    layout_description: str = Field(
        default="",
        description="Brief description of the layout and visual hierarchy",
    )
    ai_summary: str = Field(
        default="",
        description="AI-generated summary of the packaging concept",
    )
