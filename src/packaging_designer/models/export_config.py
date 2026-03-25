"""Export configuration models."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class ExportFormat(StrEnum):
    ILLUSTRATOR_JSX = "illustrator_jsx"
    INDESIGN_IDML = "indesign_idml"
    PREVIEW_PDF = "preview_pdf"
    PREVIEW_PNG = "preview_png"


class ExportConfig(BaseModel):
    """Configuration for DTP file export."""

    formats: list[ExportFormat] = Field(
        default=[ExportFormat.ILLUSTRATOR_JSX],
    )
    include_concept_image: bool = Field(
        default=True,
        description="Include original concept as reference layer",
    )
    include_back_label: bool = Field(default=False)
    bleed_mm: float = Field(default=3.0, description="Bleed in mm")
    output_dir: Path | None = None


class OutputFile(BaseModel):
    """A generated output file."""

    format: ExportFormat
    file_name: str
    content: bytes | None = Field(default=None, exclude=True)
    content_str: str | None = Field(default=None, exclude=True)
    description: str = ""


class OutputBundle(BaseModel):
    """Complete bundle of generated files."""

    files: list[OutputFile] = Field(default_factory=list)
    assets_dir: str | None = Field(
        default=None,
        description="Path to assets folder (for JSX)",
    )
