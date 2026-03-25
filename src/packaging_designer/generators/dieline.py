"""Dieline generator and DieCutTemplates API client.

Generates basic parametric dielines as SVG, or fetches from
the DieCutTemplates.com API for production-quality templates.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from packaging_designer.models.package_spec import Dimensions, PackageType


def generate_box_dieline_svg(
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    bleed_mm: float = 3,
    flap_mm: float = 15,
) -> str:
    """Generate a basic tuck-end box dieline as SVG.

    Layout (unfolded):
    [flap][back][side][front][side][glue flap]
    + top/bottom flaps

    Args:
        width_mm: Front panel width.
        height_mm: Panel height.
        depth_mm: Box depth (side panel width).
        bleed_mm: Bleed extension.
        flap_mm: Tuck flap height.

    Returns:
        SVG string with cut (solid) and fold (dashed) lines.
    """
    # Total dimensions
    total_w = flap_mm + width_mm + depth_mm + width_mm + depth_mm + flap_mm
    total_h = flap_mm + height_mm + flap_mm
    vb_w = total_w + bleed_mm * 2
    vb_h = total_h + bleed_mm * 2
    ox, oy = bleed_mm, bleed_mm  # origin offset

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{vb_w}mm" height="{vb_h}mm" '
        f'viewBox="0 0 {vb_w} {vb_h}">',
        '  <style>',
        '    .cut { stroke: #00AAFF; stroke-width: 0.3; fill: none; }',
        '    .fold { stroke: #00AAFF; stroke-width: 0.2; fill: none; stroke-dasharray: 3,2; }',
        '    .bleed { stroke: #FF00FF; stroke-width: 0.15; fill: none; stroke-dasharray: 1,1; }',
        '    .label { font-family: Arial; font-size: 3px; fill: #999; }',
        '  </style>',
    ]

    # Panel positions (x from left)
    panels = [
        ("Glue flap", ox, flap_mm),
        ("Back", ox + flap_mm, width_mm),
        ("Side L", ox + flap_mm + width_mm, depth_mm),
        ("Front", ox + flap_mm + width_mm + depth_mm, width_mm),
        ("Side R", ox + flap_mm + width_mm + depth_mm + width_mm, depth_mm),
        ("Tuck flap", ox + flap_mm + width_mm + depth_mm + width_mm + depth_mm, flap_mm),
    ]

    y_top = oy + flap_mm
    y_bottom = oy + flap_mm + height_mm

    # Main cut outline
    pts = []
    for name, x, w in panels:
        pts.append(f"{x},{y_top}")
    pts.append(f"{panels[-1][1] + panels[-1][2]},{y_top}")
    pts.append(f"{panels[-1][1] + panels[-1][2]},{y_bottom}")
    for name, x, w in reversed(panels):
        pts.append(f"{x},{y_bottom}")
    pts.append(f"{panels[0][1]},{y_top}")

    lines.append(f'  <polygon class="cut" points="{" ".join(pts)}"/>')

    # Fold lines (vertical between panels)
    for name, x, w in panels[1:]:
        lines.append(
            f'  <line class="fold" x1="{x}" y1="{y_top}" x2="{x}" y2="{y_bottom}"/>'
        )

    # Top/bottom flap fold lines
    for name, x, w in panels:
        if name in ("Back", "Front"):
            # Top flap
            lines.append(
                f'  <line class="fold" x1="{x}" y1="{y_top}" x2="{x + w}" y2="{y_top}"/>'
            )
            lines.append(
                f'  <rect class="cut" x="{x}" y="{oy}" width="{w}" height="{flap_mm}"/>'
            )
            # Bottom flap
            lines.append(
                f'  <line class="fold" x1="{x}" y1="{y_bottom}" x2="{x + w}" y2="{y_bottom}"/>'
            )
            lines.append(
                f'  <rect class="cut" x="{x}" y="{y_bottom}" width="{w}" height="{flap_mm}"/>'
            )

    # Panel labels
    for name, x, w in panels:
        lines.append(
            f'  <text class="label" x="{x + w/2}" y="{y_top + height_mm/2}" '
            f'text-anchor="middle">{name}</text>'
        )

    # Bleed outline
    lines.append(
        f'  <rect class="bleed" x="{ox - bleed_mm}" y="{oy - bleed_mm}" '
        f'width="{total_w + bleed_mm*2}" height="{total_h + bleed_mm*2}"/>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def generate_pouch_dieline_svg(
    width_mm: float,
    height_mm: float,
    bleed_mm: float = 3,
    seal_mm: float = 10,
) -> str:
    """Generate a simple pouch/sachet dieline as SVG.

    Args:
        width_mm: Pouch width.
        height_mm: Pouch height.
        bleed_mm: Bleed extension.
        seal_mm: Seal area width.

    Returns:
        SVG string.
    """
    total_w = width_mm * 2 + seal_mm  # front + back + side seal
    total_h = height_mm + seal_mm * 2  # top + bottom seal
    vb_w = total_w + bleed_mm * 2
    vb_h = total_h + bleed_mm * 2
    ox, oy = bleed_mm, bleed_mm

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{vb_w}mm" height="{vb_h}mm" '
        f'viewBox="0 0 {vb_w} {vb_h}">',
        '  <style>',
        '    .cut { stroke: #00AAFF; stroke-width: 0.3; fill: none; }',
        '    .fold { stroke: #00AAFF; stroke-width: 0.2; fill: none; stroke-dasharray: 3,2; }',
        '    .seal { stroke: #FF6600; stroke-width: 0.2; fill: rgba(255,102,0,0.05); stroke-dasharray: 2,1; }',
        '    .label { font-family: Arial; font-size: 4px; fill: #999; }',
        '  </style>',
    ]

    # Cut outline
    lines.append(
        f'  <rect class="cut" x="{ox}" y="{oy}" '
        f'width="{total_w}" height="{total_h}"/>'
    )

    # Fold line (center)
    cx = ox + width_mm
    lines.append(
        f'  <line class="fold" x1="{cx}" y1="{oy}" x2="{cx}" y2="{oy + total_h}"/>'
    )

    # Seal areas
    lines.append(f'  <rect class="seal" x="{ox}" y="{oy}" width="{total_w}" height="{seal_mm}"/>')
    lines.append(f'  <rect class="seal" x="{ox}" y="{oy + total_h - seal_mm}" width="{total_w}" height="{seal_mm}"/>')
    lines.append(f'  <rect class="seal" x="{ox + total_w - seal_mm}" y="{oy}" width="{seal_mm}" height="{total_h}"/>')

    # Labels
    lines.append(
        f'  <text class="label" x="{ox + width_mm/2}" y="{oy + total_h/2}" '
        f'text-anchor="middle">Front</text>'
    )
    lines.append(
        f'  <text class="label" x="{ox + width_mm + width_mm/2}" y="{oy + total_h/2}" '
        f'text-anchor="middle">Back</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def generate_label_dieline_svg(
    width_mm: float,
    height_mm: float,
    bleed_mm: float = 2,
) -> str:
    """Generate a simple rectangular label dieline."""
    vb_w = width_mm + bleed_mm * 2
    vb_h = height_mm + bleed_mm * 2

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{vb_w}mm" height="{vb_h}mm" '
        f'viewBox="0 0 {vb_w} {vb_h}">\n'
        f'  <rect x="{bleed_mm}" y="{bleed_mm}" '
        f'width="{width_mm}" height="{height_mm}" '
        f'fill="none" stroke="#00AAFF" stroke-width="0.3"/>\n'
        f'  <rect x="0" y="0" width="{vb_w}" height="{vb_h}" '
        f'fill="none" stroke="#FF00FF" stroke-width="0.15" stroke-dasharray="1,1"/>\n'
        f'</svg>'
    )


def get_dieline_svg(
    package_type: str,
    width_mm: float,
    height_mm: float,
    depth_mm: float | None = None,
    bleed_mm: float = 3,
) -> str:
    """Get appropriate dieline SVG for package type."""
    if package_type in ("box", "tray") and depth_mm:
        return generate_box_dieline_svg(width_mm, height_mm, depth_mm, bleed_mm)
    elif package_type in ("pouch", "standup_pouch", "sachet"):
        return generate_pouch_dieline_svg(width_mm, height_mm, bleed_mm)
    else:
        return generate_label_dieline_svg(width_mm, height_mm, bleed_mm)


async def fetch_dieline_from_api(
    box_type: str,
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    api_key: str | None = None,
) -> str | None:
    """Fetch production dieline from DieCutTemplates.com API.

    Args:
        box_type: FEFCO code or template name (e.g. '0201', 'tuck_end').
        width_mm, height_mm, depth_mm: Dimensions.
        api_key: DieCutTemplates API key.

    Returns:
        SVG string or None if API unavailable.
    """
    if not api_key:
        logger.info("DieCutTemplates API key not configured \u2014 using built-in dieline")
        return None

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.diecuttemplates.com/api/v1/dielines",
                params={
                    "type": box_type,
                    "width": width_mm,
                    "height": height_mm,
                    "depth": depth_mm,
                    "format": "svg",
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                logger.info("Dieline fetched from DieCutTemplates API")
                return resp.text
            else:
                logger.warning(f"DieCutTemplates API error: {resp.status_code}")
    except Exception as e:
        logger.warning(f"DieCutTemplates API failed: {e}")
    return None
