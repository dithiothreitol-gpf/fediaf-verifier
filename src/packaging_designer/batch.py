"""Batch processing \u2014 process multiple packaging concepts in one run.

Takes a list of images and generates DTP files for each.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

from loguru import logger

if TYPE_CHECKING:
    from fediaf_verifier.providers import AIProvider


@dataclass
class BatchItem:
    """Single item in a batch run."""

    filename: str
    image_bytes: bytes
    media_type: str = "image/png"
    product_context: str = ""


@dataclass
class BatchResult:
    """Result for a single batch item."""

    filename: str
    success: bool = False
    jsx_content: str | None = None
    idml_bytes: bytes | None = None
    error: str | None = None


def run_batch(
    items: list[BatchItem],
    provider: AIProvider,
    generate_jsx: bool = True,
    generate_idml: bool = True,
    bleed_mm: float = 3.0,
    on_progress: callable | None = None,
) -> list[BatchResult]:
    """Process multiple packaging concepts.

    Args:
        items: List of images to process.
        provider: AI provider for analysis.
        generate_jsx: Whether to generate Illustrator JSX.
        generate_idml: Whether to generate InDesign IDML.
        bleed_mm: Bleed in mm.
        on_progress: Callback(current, total, filename) for progress updates.

    Returns:
        List of BatchResult, one per input item.
    """
    from packaging_designer.builders.idml_builder import build_idml
    from packaging_designer.builders.jsx_builder import build_jsx
    from packaging_designer.enricher import enrich
    from packaging_designer.models.export_config import ExportConfig
    from packaging_designer.pipeline import run_analysis

    results = []
    config = ExportConfig(bleed_mm=bleed_mm)

    for i, item in enumerate(items):
        logger.info(f"Batch [{i+1}/{len(items)}]: {item.filename}")
        if on_progress:
            on_progress(i + 1, len(items), item.filename)

        try:
            # Analyze
            analysis = run_analysis(
                image_bytes=item.image_bytes,
                media_type=item.media_type,
                provider=provider,
                product_context=item.product_context,
            )

            # Enrich (auto-select mandatory elements)
            enrichment = enrich(analysis)
            mandatory_ids = [
                m.element_id
                for m in enrichment.missing_elements
                if m.priority.value == "mandatory"
            ]
            if mandatory_ids:
                enrichment = enrich(analysis, selected_ids=mandatory_ids)

            result = BatchResult(filename=item.filename, success=True)

            if generate_jsx:
                result.jsx_content = build_jsx(
                    analysis=analysis,
                    enrichment=enrichment,
                    config=config,
                )

            if generate_idml:
                result.idml_bytes = build_idml(
                    analysis=analysis,
                    enrichment=enrichment,
                    config=config,
                )

            results.append(result)

        except Exception as e:
            logger.error(f"Batch item {item.filename} failed: {e}")
            results.append(
                BatchResult(filename=item.filename, success=False, error=str(e))
            )

    return results


def package_batch_results(
    results: list[BatchResult],
    include_jsx: bool = True,
    include_idml: bool = True,
) -> bytes:
    """Package all batch results into a single ZIP file.

    Structure:
        batch_output/
            product_1/
                packaging_design.jsx
                packaging_design.idml
            product_2/
                ...
            _errors.txt  (if any failures)

    Returns:
        ZIP file bytes.
    """
    buf = BytesIO()
    errors = []

    with ZipFile(buf, "w") as zf:
        for r in results:
            stem = Path(r.filename).stem

            if r.success:
                if include_jsx and r.jsx_content:
                    zf.writestr(
                        f"batch_output/{stem}/packaging_design.jsx",
                        r.jsx_content,
                    )
                if include_idml and r.idml_bytes:
                    zf.writestr(
                        f"batch_output/{stem}/packaging_design.idml",
                        r.idml_bytes,
                    )
            else:
                errors.append(f"{r.filename}: {r.error}")

        if errors:
            zf.writestr(
                "batch_output/_errors.txt",
                "\n".join(errors),
            )

    return buf.getvalue()
