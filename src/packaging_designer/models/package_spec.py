"""Package specification models — type, dimensions, dieline."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PackageType(StrEnum):
    BOX = "box"
    POUCH = "pouch"
    STANDUP_POUCH = "standup_pouch"
    CAN = "can"
    BOTTLE = "bottle"
    SACHET = "sachet"
    TUBE = "tube"
    LABEL = "label"
    TRAY = "tray"
    BAG = "bag"
    OTHER = "other"


class ProductCategory(StrEnum):
    PET_FOOD = "pet_food"
    FOOD = "food"
    COSMETICS = "cosmetics"
    SUPPLEMENTS = "supplements"
    OTHER = "other"


class Dimensions(BaseModel):
    """Physical dimensions in millimeters."""

    width_mm: float = Field(description="Width in mm")
    height_mm: float = Field(description="Height in mm")
    depth_mm: float | None = Field(default=None, description="Depth in mm (for boxes)")

    @property
    def width_pt(self) -> float:
        """Width in PostScript points (1pt = 1/72 inch)."""
        return self.width_mm * 2.834645669

    @property
    def height_pt(self) -> float:
        """Height in PostScript points."""
        return self.height_mm * 2.834645669


class PackageSpec(BaseModel):
    """Identified packaging specification from concept image."""

    package_type: PackageType = Field(description="Type of packaging")
    dimensions: Dimensions = Field(description="Estimated dimensions")
    sides_visible: int = Field(default=1, description="Number of sides visible in concept")
    product_category: ProductCategory = Field(default=ProductCategory.PET_FOOD)
    dieline_type: str | None = Field(
        default=None,
        description="Structural dieline type, e.g. 'tuck_end', 'pillow_pouch'",
    )
    product_name: str = Field(default="", description="Detected product name")
    brand_name: str = Field(default="", description="Detected brand name")
