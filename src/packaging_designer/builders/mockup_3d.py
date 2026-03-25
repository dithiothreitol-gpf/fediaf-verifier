"""Simple 3D mockup generator using Pillow perspective transforms.

Creates a basic 3D-like preview of packaging by applying perspective
transforms to the front and side views. This is a lightweight
approximation \u2014 not a true 3D renderer.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from packaging_designer.utils.color import hex_to_rgb

if TYPE_CHECKING:
    from packaging_designer.models.design_elements import DesignAnalysis


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def generate_3d_mockup(
    analysis: DesignAnalysis,
    concept_image: bytes | None = None,
    output_width: int = 800,
) -> bytes:
    """Generate a simple 3D-ish mockup of the packaging.

    For boxes: shows front + right side with slight perspective.
    For pouches/cans: shows front with shadow and reflection effect.

    Args:
        analysis: Design analysis with package spec and colors.
        concept_image: Original concept image bytes.
        output_width: Output image width in pixels.

    Returns:
        PNG bytes.
    """
    spec = analysis.package_spec
    dims = spec.dimensions
    pkg_type = spec.package_type.value

    # Determine aspect ratio and create canvas
    aspect = dims.height_mm / dims.width_mm
    front_w = int(output_width * 0.55)
    front_h = int(front_w * aspect)
    canvas_w = output_width
    canvas_h = int(front_h * 1.3)

    # Background
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (240, 240, 240, 255))
    draw = ImageDraw.Draw(canvas)

    # Background color from analysis
    bg_swatch = next(
        (s for s in analysis.color_swatches if s.role == "background"),
        None,
    )
    primary = next(
        (s for s in analysis.color_swatches if s.role == "primary"),
        None,
    )

    front_color = hex_to_rgb(primary.hex) if primary else (60, 120, 180)
    bg_color = hex_to_rgb(bg_swatch.hex) if bg_swatch else (255, 255, 255)

    # Front face position
    fx = int(canvas_w * 0.15)
    fy = int(canvas_h * 0.1)

    if pkg_type in ("box", "tray"):
        # Box: front face + right side panel
        depth_ratio = (dims.depth_mm or 40) / dims.width_mm
        side_w = int(front_w * depth_ratio * 0.6)  # perspective foreshortening
        skew_y = int(front_h * 0.08)

        # Shadow
        shadow_offset = 8
        draw.polygon(
            [
                (fx + shadow_offset, fy + front_h + shadow_offset),
                (fx + front_w + shadow_offset, fy + front_h + shadow_offset),
                (fx + front_w + side_w + shadow_offset, fy + front_h - skew_y + shadow_offset),
                (fx + front_w + side_w + shadow_offset, fy + skew_y + shadow_offset),
                (fx + front_w + shadow_offset, fy + shadow_offset),
                (fx + shadow_offset, fy + shadow_offset),
            ],
            fill=(0, 0, 0, 40),
        )

        # Front face
        draw.rectangle([fx, fy, fx + front_w, fy + front_h], fill=front_color)

        # Right side (darker shade for 3D effect)
        dark_color = tuple(max(0, c - 40) for c in front_color)
        draw.polygon(
            [
                (fx + front_w, fy),
                (fx + front_w + side_w, fy + skew_y),
                (fx + front_w + side_w, fy + front_h - skew_y),
                (fx + front_w, fy + front_h),
            ],
            fill=dark_color,
        )

        # Top face (lighter)
        light_color = tuple(min(255, c + 30) for c in front_color)
        draw.polygon(
            [
                (fx, fy),
                (fx + front_w, fy),
                (fx + front_w + side_w, fy + skew_y),
                (fx + side_w, fy + skew_y),
            ],
            fill=light_color,
        )

    elif pkg_type in ("pouch", "standup_pouch", "sachet"):
        # Pouch: rounded bottom, slight bulge
        shadow_offset = 6
        draw.ellipse(
            [fx + shadow_offset, fy + front_h - 20 + shadow_offset,
             fx + front_w + shadow_offset, fy + front_h + 20 + shadow_offset],
            fill=(0, 0, 0, 30),
        )
        draw.rounded_rectangle(
            [fx, fy, fx + front_w, fy + front_h],
            radius=15,
            fill=front_color,
        )
        # Seal line at top
        draw.line(
            [fx + 10, fy + 8, fx + front_w - 10, fy + 8],
            fill=tuple(max(0, c - 30) for c in front_color),
            width=3,
        )

    else:
        # Generic: simple rectangle with shadow
        draw.rectangle(
            [fx + 5, fy + 5, fx + front_w + 5, fy + front_h + 5],
            fill=(0, 0, 0, 30),
        )
        draw.rectangle([fx, fy, fx + front_w, fy + front_h], fill=front_color)

    # Overlay concept image if provided
    if concept_image:
        try:
            concept = Image.open(BytesIO(concept_image)).convert("RGBA")
            concept = concept.resize((front_w, front_h), Image.Resampling.LANCZOS)
            concept.putalpha(220)
            canvas.paste(concept, (fx, fy), concept)
        except Exception:
            pass

    # Product name text
    font = _get_font(max(16, front_w // 12))
    product_name = spec.product_name or "Product"
    text_color = (255, 255, 255) if sum(front_color) < 400 else (30, 30, 30)
    draw.text(
        (fx + front_w // 2, fy + front_h // 3),
        product_name,
        fill=(*text_color, 200),
        font=font,
        anchor="mm",
    )

    # Package type label
    font_sm = _get_font(12)
    draw.text(
        (canvas_w // 2, canvas_h - 20),
        f"{spec.package_type.value} \u2014 {dims.width_mm:.0f}\u00d7{dims.height_mm:.0f} mm",
        fill=(120, 120, 120, 200),
        font=font_sm,
        anchor="mm",
    )

    canvas = canvas.convert("RGB")
    buf = BytesIO()
    canvas.save(buf, format="PNG", quality=95)
    return buf.getvalue()
