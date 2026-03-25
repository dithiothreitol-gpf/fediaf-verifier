"""Nutrition/analytical constituents table generator.

Generates SVG or plain text tables for analytical constituents
(pet food) or nutrition facts (food).
"""

from __future__ import annotations


def generate_nutrition_svg(
    constituents: dict[str, str],
    title: str = "Sk\u0142adniki analityczne",
    width_mm: float = 60,
    font_size: float = 7,
) -> str:
    """Generate an SVG nutrition/analytical table.

    Args:
        constituents: Dict of name→value, e.g. {"Bia\u0142ko": "32%", "T\u0142uszcz": "15%"}.
        title: Table title.
        width_mm: Table width in mm.
        font_size: Font size in pt.

    Returns:
        SVG string.
    """
    row_height = font_size * 1.8
    header_height = font_size * 2.2
    padding = 3
    n_rows = len(constituents)
    total_height = header_height + (n_rows * row_height) + padding * 2

    # Convert mm to SVG units (1mm = 3.78px approx)
    w = width_mm * 3.78
    h = total_height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.1f}" height="{h:.1f}" '
        f'viewBox="0 0 {w:.1f} {h:.1f}">',
        f'  <rect width="{w:.1f}" height="{h:.1f}" fill="none" stroke="#333" stroke-width="0.5"/>',
    ]

    # Header
    y = padding + font_size
    lines.append(
        f'  <text x="{padding}" y="{y:.1f}" '
        f'font-family="Arial, sans-serif" font-size="{font_size + 1}" '
        f'font-weight="bold" fill="#000">{_esc_xml(title)}</text>'
    )
    y_line = y + 3
    lines.append(
        f'  <line x1="0" y1="{y_line:.1f}" x2="{w:.1f}" y2="{y_line:.1f}" '
        f'stroke="#333" stroke-width="0.5"/>'
    )

    # Rows
    y = header_height + padding
    value_x = w * 0.65
    for name, value in constituents.items():
        lines.append(
            f'  <text x="{padding}" y="{y:.1f}" '
            f'font-family="Arial, sans-serif" font-size="{font_size}" '
            f'fill="#000">{_esc_xml(name)}</text>'
        )
        lines.append(
            f'  <text x="{value_x:.1f}" y="{y:.1f}" '
            f'font-family="Arial, sans-serif" font-size="{font_size}" '
            f'fill="#000" text-anchor="end">{_esc_xml(value)}</text>'
        )
        y += row_height

    lines.append("</svg>")
    return "\n".join(lines)


def generate_feeding_table_svg(
    rows: list[tuple[str, str]],
    title: str = "Zalecenia \u017cywieniowe",
    width_mm: float = 65,
    font_size: float = 6.5,
) -> str:
    """Generate an SVG feeding guidelines table.

    Args:
        rows: List of (weight_range, daily_amount) tuples.
        title: Table title.
        width_mm: Table width in mm.
        font_size: Font size in pt.

    Returns:
        SVG string.
    """
    row_height = font_size * 2
    header_row_height = font_size * 2.2
    padding = 3
    total_height = header_row_height * 2 + len(rows) * row_height + padding * 2

    w = width_mm * 3.78
    h = total_height
    col_split = w * 0.5

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.1f}" height="{h:.1f}" '
        f'viewBox="0 0 {w:.1f} {h:.1f}">',
        f'  <rect width="{w:.1f}" height="{h:.1f}" fill="none" stroke="#333" stroke-width="0.5"/>',
    ]

    # Title
    y = padding + font_size
    lines.append(
        f'  <text x="{w/2:.1f}" y="{y:.1f}" text-anchor="middle" '
        f'font-family="Arial, sans-serif" font-size="{font_size + 1}" '
        f'font-weight="bold" fill="#000">{_esc_xml(title)}</text>'
    )
    y += header_row_height

    # Column headers
    lines.append(
        f'  <text x="{padding}" y="{y:.1f}" '
        f'font-family="Arial, sans-serif" font-size="{font_size}" '
        f'font-weight="bold" fill="#333">Masa cia\u0142a</text>'
    )
    lines.append(
        f'  <text x="{col_split + padding}" y="{y:.1f}" '
        f'font-family="Arial, sans-serif" font-size="{font_size}" '
        f'font-weight="bold" fill="#333">Dawka dzienna</text>'
    )
    y_line = y + 3
    lines.append(
        f'  <line x1="0" y1="{y_line:.1f}" x2="{w:.1f}" y2="{y_line:.1f}" '
        f'stroke="#333" stroke-width="0.3"/>'
    )
    y += row_height

    # Data rows
    for weight, amount in rows:
        lines.append(
            f'  <text x="{padding}" y="{y:.1f}" '
            f'font-family="Arial, sans-serif" font-size="{font_size}" '
            f'fill="#000">{_esc_xml(weight)}</text>'
        )
        lines.append(
            f'  <text x="{col_split + padding}" y="{y:.1f}" '
            f'font-family="Arial, sans-serif" font-size="{font_size}" '
            f'fill="#000">{_esc_xml(amount)}</text>'
        )
        y += row_height

    # Vertical divider
    lines.append(
        f'  <line x1="{col_split:.1f}" y1="{header_row_height:.1f}" '
        f'x2="{col_split:.1f}" y2="{h:.1f}" stroke="#333" stroke-width="0.3"/>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def _esc_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
