"""Annotate PDF and image files with detected label structure issues.

Uses pymupdf (fitz) for PDF annotation and Pillow for images.
All coordinates are normalized 0-1000 in the AI response and scaled
to actual document/image dimensions here.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from fediaf_verifier.models.label_structure import (
        GlyphIssue,
        LabelStructureReport,
        StructureIssue,
    )

# -- Color constants (RGB tuples 0-1 for pymupdf, 0-255 for Pillow) ----

_COLOR_CRITICAL = (0.86, 0.2, 0.2)       # red
_COLOR_WARNING = (1.0, 0.7, 0.0)         # orange
_COLOR_INFO = (0.2, 0.5, 0.9)            # blue
_COLOR_GLYPH = (0.8, 0.0, 0.6)           # magenta

_PIL_CRITICAL = (220, 50, 50)
_PIL_WARNING = (255, 180, 0)
_PIL_INFO = (50, 130, 230)
_PIL_GLYPH = (204, 0, 153)

_SEVERITY_COLORS = {
    "critical": _COLOR_CRITICAL,
    "warning": _COLOR_WARNING,
    "info": _COLOR_INFO,
}
_PIL_SEVERITY_COLORS = {
    "critical": _PIL_CRITICAL,
    "warning": _PIL_WARNING,
    "info": _PIL_INFO,
}


def _bbox_to_rect(
    bbox: list[int | float], page_width: float, page_height: float,
) -> tuple[float, float, float, float] | None:
    """Convert normalized 0-1000 bbox to absolute coordinates.

    Returns (x0, y0, x1, y1) in document units, or None if bbox is invalid.
    """
    if not bbox or len(bbox) != 4:
        return None
    try:
        x, y, w, h = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return None
    scale_x = page_width / 1000.0
    scale_y = page_height / 1000.0
    x0 = x * scale_x
    y0 = y * scale_y
    x1 = (x + w) * scale_x
    y1 = (y + h) * scale_y
    return x0, y0, x1, y1


# -- PDF annotation via pymupdf ----------------------------------------


def annotate_pdf(
    pdf_bytes: bytes,
    report: LabelStructureReport,
) -> bytes | None:
    """Add rectangle annotations to a PDF file.

    Args:
        pdf_bytes: Original PDF file content.
        report: Label structure report with bbox coordinates.

    Returns:
        Annotated PDF as bytes, or None if pymupdf unavailable.
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        logger.warning("pymupdf not installed — PDF annotation skipped")
        return None

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error("Cannot open PDF for annotation: {}", e)
        return None

    page = doc[0]
    pw, ph = page.rect.width, page.rect.height

    # Annotate structure issues
    for issue in report.structure_issues:
        if not issue.bbox:
            continue
        coords = _bbox_to_rect(issue.bbox, pw, ph)
        if not coords:
            continue
        rect = fitz.Rect(coords)
        color = _SEVERITY_COLORS.get(issue.severity, _COLOR_WARNING)
        annot = page.add_rect_annot(rect)
        annot.set_colors(stroke=color)
        annot.set_border(width=2)
        annot.set_opacity(0.7)
        annot.set_info(
            title=f"[{issue.severity.upper()}] {issue.issue_type}",
            content=issue.description,
        )
        annot.update()

        # Add label text above the rectangle
        label = f"[{issue.issue_type}]"
        label_point = fitz.Point(rect.x0, max(rect.y0 - 4, 2))
        page.insert_text(
            label_point,
            label,
            fontsize=7,
            color=color,
        )

    # Annotate glyph issues
    for glyph in report.glyph_issues:
        if not glyph.bbox:
            continue
        coords = _bbox_to_rect(glyph.bbox, pw, ph)
        if not coords:
            continue
        rect = fitz.Rect(coords)
        annot = page.add_rect_annot(rect)
        annot.set_colors(stroke=_COLOR_GLYPH)
        annot.set_border(width=2, dashes=[3, 2])
        annot.set_opacity(0.7)
        annot.set_info(
            title=f"[{glyph.language_code.upper()}] {glyph.issue_type}",
            content=(
                f"{glyph.affected_text} → {glyph.expected_text}\n"
                f"{glyph.explanation}"
            ),
        )
        annot.update()

        label = f"[{glyph.issue_type}] {glyph.language_code.upper()}"
        label_point = fitz.Point(rect.x0, max(rect.y0 - 4, 2))
        page.insert_text(
            label_point,
            label,
            fontsize=7,
            color=_COLOR_GLYPH,
        )

    # Annotate language section boundaries (lighter, dashed)
    for sec in report.language_sections:
        if not sec.bbox:
            continue
        coords = _bbox_to_rect(sec.bbox, pw, ph)
        if not coords:
            continue
        rect = fitz.Rect(coords)
        if sec.content_complete and sec.marker_present:
            color = (0.3, 0.7, 0.3)  # green = OK
        else:
            color = _COLOR_WARNING
        annot = page.add_rect_annot(rect)
        annot.set_colors(stroke=color)
        annot.set_border(width=1, dashes=[5, 3])
        annot.set_opacity(0.4)
        annot.set_info(
            title=f"Sekcja: {sec.language_code.upper()}",
            content=sec.language_name,
        )
        annot.update()

        # Section label
        label_point = fitz.Point(rect.x0, max(rect.y0 - 2, 2))
        page.insert_text(
            label_point,
            sec.language_code.upper(),
            fontsize=8,
            color=color,
        )

    result = doc.tobytes()
    doc.close()
    return result


# -- Image annotation via Pillow ----------------------------------------


def annotate_image(
    image_bytes: bytes,
    report: LabelStructureReport,
) -> bytes | None:
    """Draw annotation rectangles on an image.

    Args:
        image_bytes: Original image file content (JPG/PNG).
        report: Label structure report with bbox coordinates.

    Returns:
        Annotated image as PNG bytes, or None on error.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — image annotation skipped")
        return None

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        logger.error("Cannot open image for annotation: {}", e)
        return None

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    iw, ih = img.size

    # Try to load a small font for labels
    try:
        font = ImageFont.truetype("arial.ttf", max(12, ih // 80))
    except (OSError, IOError):
        font = ImageFont.load_default()

    def _draw_rect(
        bbox: list[int | float],
        color: tuple[int, int, int],
        label: str,
        width: int = 3,
    ) -> None:
        coords = _bbox_to_rect(bbox, iw, ih)
        if not coords:
            return
        x0, y0, x1, y1 = coords
        # Semi-transparent fill
        draw.rectangle(
            [x0, y0, x1, y1],
            outline=(*color, 200),
            width=width,
        )
        # Fill with very light tint
        draw.rectangle(
            [x0 + width, y0 + width, x1 - width, y1 - width],
            fill=(*color, 30),
        )
        # Label background + text
        if label:
            tw = draw.textlength(label, font=font)
            label_y = max(y0 - 18, 0)
            draw.rectangle(
                [x0, label_y, x0 + tw + 8, label_y + 16],
                fill=(*color, 180),
            )
            draw.text(
                (x0 + 4, label_y + 1),
                label,
                fill=(255, 255, 255, 255),
                font=font,
            )

    # Structure issues
    for issue in report.structure_issues:
        if not issue.bbox:
            continue
        color = _PIL_SEVERITY_COLORS.get(issue.severity, _PIL_WARNING)
        _draw_rect(issue.bbox, color, f"{issue.issue_type}")

    # Glyph issues
    for glyph in report.glyph_issues:
        if not glyph.bbox:
            continue
        _draw_rect(
            glyph.bbox,
            _PIL_GLYPH,
            f"{glyph.language_code.upper()} {glyph.issue_type}",
            width=2,
        )

    # Language sections (lighter borders)
    for sec in report.language_sections:
        if not sec.bbox:
            continue
        ok = sec.content_complete and sec.marker_present
        color = (60, 180, 60) if ok else _PIL_WARNING
        _draw_rect(sec.bbox, color, sec.language_code.upper(), width=1)

    # Composite
    result = Image.alpha_composite(img, overlay)
    # Convert to RGB for output (PNG supports RGBA but JPG doesn't)
    output = result.convert("RGB")

    buf = io.BytesIO()
    output.save(buf, format="PNG")
    return buf.getvalue()


# -- Unified entry point ------------------------------------------------


def annotate_file(
    file_bytes: bytes,
    media_type: str,
    report: LabelStructureReport,
) -> tuple[bytes | None, str]:
    """Annotate a file based on its media type.

    Returns:
        Tuple of (annotated_bytes, output_media_type) or (None, "") on failure.
    """
    has_annotations = any(
        item.bbox
        for item in (
            *report.structure_issues,
            *report.glyph_issues,
            *report.language_sections,
        )
    )
    if not has_annotations:
        logger.info("No bounding boxes in report — skipping annotation")
        return None, ""

    if media_type == "application/pdf":
        result = annotate_pdf(file_bytes, report)
        if result:
            return result, "application/pdf"
        return None, ""

    if media_type in ("image/jpeg", "image/png"):
        result = annotate_image(file_bytes, report)
        if result:
            return result, "image/png"
        return None, ""

    logger.warning("Unsupported media type for annotation: {}", media_type)
    return None, ""
