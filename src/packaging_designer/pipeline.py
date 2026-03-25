"""Packaging designer pipeline — orchestrates analysis → enrichment → export.

Central orchestration module that ties all phases together.
"""

from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

from loguru import logger

from packaging_designer.analyzer import analyze_concept
from packaging_designer.builders.jsx_builder import build_jsx
from packaging_designer.builders.preview_builder import build_preview_png
from packaging_designer.enricher import enrich
from packaging_designer.models.design_elements import DesignAnalysis
from packaging_designer.models.enrichment import EnrichmentResult
from packaging_designer.models.export_config import (
    ExportConfig,
    ExportFormat,
    OutputBundle,
    OutputFile,
)

if TYPE_CHECKING:
    from fediaf_verifier.providers import AIProvider


def run_analysis(
    image_bytes: bytes,
    media_type: str,
    provider: AIProvider,
    product_context: str = "",
    max_tokens: int = 4096,
) -> DesignAnalysis:
    """Phase 1: Analyze concept image."""
    logger.info("Pipeline Phase 1: Analyzing concept image...")
    return analyze_concept(
        image_bytes=image_bytes,
        media_type=media_type,
        provider=provider,
        max_tokens=max_tokens,
        product_context=product_context,
    )


def run_enrichment(
    analysis: DesignAnalysis,
    selected_ids: list[str] | None = None,
    ean_number: str | None = None,
) -> EnrichmentResult:
    """Phase 2: Detect missing elements, optionally generate assets."""
    logger.info("Pipeline Phase 2: Enrichment...")
    return enrich(analysis, selected_ids=selected_ids, ean_number=ean_number)


def run_export(
    analysis: DesignAnalysis,
    enrichment: EnrichmentResult | None = None,
    concept_image: bytes | None = None,
    config: ExportConfig | None = None,
) -> OutputBundle:
    """Phase 3: Generate DTP output files.

    Args:
        analysis: Design analysis from Phase 1.
        enrichment: Optional enrichment from Phase 2.
        concept_image: Original concept image bytes.
        config: Export configuration.

    Returns:
        OutputBundle with generated files.
    """
    config = config or ExportConfig()
    bundle = OutputBundle()
    logger.info(f"Pipeline Phase 3: Exporting {[f.value for f in config.formats]}...")

    # Generate Illustrator JSX
    if ExportFormat.ILLUSTRATOR_JSX in config.formats:
        jsx_content = build_jsx(
            analysis=analysis,
            enrichment=enrichment,
            config=config,
            include_concept=config.include_concept_image,
        )
        bundle.files.append(
            OutputFile(
                format=ExportFormat.ILLUSTRATOR_JSX,
                file_name="packaging_design.jsx",
                content_str=jsx_content,
                description="Illustrator ExtendScript — uruchom w File > Scripts",
            )
        )

    # Generate preview PNG
    if ExportFormat.PREVIEW_PNG in config.formats:
        png_bytes = build_preview_png(
            analysis=analysis,
            concept_image=concept_image,
        )
        bundle.files.append(
            OutputFile(
                format=ExportFormat.PREVIEW_PNG,
                file_name="preview.png",
                content=png_bytes,
                description="Podglad PNG z zaznaczonymi elementami",
            )
        )

    logger.info(f"Export complete: {len(bundle.files)} files generated")
    return bundle


def create_jsx_package(
    jsx_content: str,
    enrichment: EnrichmentResult | None = None,
    concept_image: bytes | None = None,
) -> bytes:
    """Create a ZIP package containing the JSX script and assets folder.

    The ZIP structure:
        packaging_design.jsx
        assets/
            concept_original.png  (if provided)
            ean_barcode.svg       (if generated)
            mobius_loop.svg       (if generated)
            ...

    Returns:
        ZIP file bytes.
    """
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        # JSX script
        zf.writestr("packaging_design.jsx", jsx_content)

        # Concept image as reference
        if concept_image:
            zf.writestr("assets/concept_original.png", concept_image)

        # Generated assets
        if enrichment:
            for asset in enrichment.generated_assets:
                if asset.svg_content:
                    zf.writestr(
                        f"assets/{asset.file_name}",
                        asset.svg_content,
                    )

    return buf.getvalue()
