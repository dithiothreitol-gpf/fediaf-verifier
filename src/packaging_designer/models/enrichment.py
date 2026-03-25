"""Enrichment models — missing elements detection and generation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ElementPriority(StrEnum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class MissingElement(BaseModel):
    """An element that should be on the packaging but was not detected."""

    element_id: str = Field(description="ID: ean_barcode, recycling_mobius, nutrition_table, etc.")
    display_name: str = Field(description="Human-readable name for UI")
    priority: ElementPriority = Field(default=ElementPriority.RECOMMENDED)
    regulation: str | None = Field(
        default=None,
        description="Regulatory reference, e.g. 'EU 1169/2011 Art.9'",
    )
    description: str = Field(default="", description="Why this element is needed")
    category: str = Field(
        default="regulatory",
        description="Category: regulatory, informational, branding",
    )


class GeneratedAsset(BaseModel):
    """An asset generated for inclusion in the DTP file."""

    element_id: str
    file_name: str = Field(description="Filename in assets folder")
    svg_content: str | None = Field(default=None, description="SVG string if inline")
    file_path: str | None = Field(default=None, description="Path to generated file")
    width_mm: float = Field(default=20)
    height_mm: float = Field(default=20)


class EnrichmentResult(BaseModel):
    """Result of the enrichment phase."""

    missing_elements: list[MissingElement] = Field(default_factory=list)
    selected_additions: list[str] = Field(
        default_factory=list,
        description="IDs of elements user chose to add",
    )
    generated_assets: list[GeneratedAsset] = Field(default_factory=list)
