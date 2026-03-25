"""Preview builder — generates PNG mockup of the packaging layout.

Uses Pillow to draw a simplified preview of the packaging with
detected elements overlaid. This is for quick review in the UI,
not for print production.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from packaging_designer.utils.color import hex_to_rgb

if TYPE_CHECKING:
    from packaging_designer.models.design_elements import DesignAnalysis


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to get Arial font, fall back to default."""
    for path in [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def build_preview_png(
    analysis: DesignAnalysis,
    concept_image: bytes | None = None,
    scale: float = 2.0,
) -> bytes:
    """Build a PNG preview showing the analyzed layout.

    Args:
        analysis: Design analysis with element positions.
        concept_image: Original concept image bytes (optional overlay).
        scale: Pixels per mm for preview resolution.

    Returns:
        PNG image bytes.
    """
    dims = analysis.package_spec.dimensions
    w = int(dims.width_mm * scale)
    h = int(dims.height_mm * scale)

    # Start with concept image or white background
    if concept_image:
        try:
            img = Image.open(BytesIO(concept_image))
            img = img.resize((w, h), Image.Resampling.LANCZOS)
            img = img.convert("RGBA")
        except Exception:
            img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    else:
        # Use background color if available
        bg_swatch = next(
            (s for s in analysis.color_swatches if s.role == "background"),
            None,
        )
        bg_color = hex_to_rgb(bg_swatch.hex) if bg_swatch else (255, 255, 255)
        img = Image.new("RGBA", (w, h), (*bg_color, 255))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_sm = _get_font(max(8, int(6 * scale)))
    font_lg = _get_font(max(12, int(10 * scale)))

    # Draw text block regions
    for tb in analysis.text_blocks:
        if not tb.bbox or len(tb.bbox) < 4:
            continue
        nx, ny, nw, nh = tb.bbox
        x1 = int((nx / 1000.0) * w)
        y1 = int((ny / 1000.0) * h)
        x2 = int(((nx + nw) / 1000.0) * w)
        y2 = int(((ny + nh) / 1000.0) * h)

        # Semi-transparent blue overlay
        draw.rectangle([x1, y1, x2, y2], outline=(50, 130, 230, 180), width=2)
        # Label
        label = f"[{tb.role}]"
        draw.text((x1 + 2, y1 + 2), label, fill=(50, 130, 230, 220), font=font_sm)

    # Draw graphic regions
    for gr in analysis.graphic_regions:
        if not gr.bbox or len(gr.bbox) < 4:
            continue
        nx, ny, nw, nh = gr.bbox
        x1 = int((nx / 1000.0) * w)
        y1 = int((ny / 1000.0) * h)
        x2 = int(((nx + nw) / 1000.0) * w)
        y2 = int(((ny + nh) / 1000.0) * h)

        draw.rectangle([x1, y1, x2, y2], outline=(60, 180, 60, 180), width=2)
        draw.text(
            (x1 + 2, y1 + 2),
            f"[{gr.region_type}]",
            fill=(60, 180, 60, 220),
            font=font_sm,
        )

    # Draw color palette strip at bottom
    swatch_size = max(15, int(12 * scale))
    palette_y = h - swatch_size - 4
    for i, cs in enumerate(analysis.color_swatches[:8]):
        sx = 4 + i * (swatch_size + 4)
        try:
            rgb = hex_to_rgb(cs.hex)
            draw.rectangle(
                [sx, palette_y, sx + swatch_size, palette_y + swatch_size],
                fill=(*rgb, 255),
                outline=(0, 0, 0, 128),
            )
        except (ValueError, IndexError):
            pass

    # Title
    title = f"{analysis.package_spec.product_name or 'Packaging'} — {analysis.package_spec.package_type.value}"
    draw.text((4, 4), title, fill=(0, 0, 0, 200), font=font_lg)

    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()
