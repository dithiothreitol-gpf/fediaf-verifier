"""Color conversion utilities — RGB to CMYK for print packaging.

NOTE ON CMYK ACCURACY:
Simple mathematical RGB→CMYK conversion (used here) does NOT match
ICC profile-based conversion. Professional results require:
- Illustrator: Edit > Assign Profile > ISO Coated v2 (FOGRA39)
- The CMYK values here are starting points — designers MUST verify
  and adjust in their DTP application with proper color management.

For critical color matching, use colormath library with Lab intermediary,
or let Illustrator handle the conversion after import.
"""

from __future__ import annotations


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple.

    Handles formats: '#RRGGBB', 'RRGGBB', '#RGB'.
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) != 6:
        return (0, 0, 0)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (0, 0, 0)


def rgb_to_cmyk(r: int, g: int, b: int) -> tuple[float, float, float, float]:
    """Convert RGB (0-255) to CMYK (0-100).

    Uses the standard mathematical conversion (no ICC profile).
    Results are approximate — see module docstring for accuracy notes.
    """
    if r == 0 and g == 0 and b == 0:
        return (0.0, 0.0, 0.0, 100.0)

    r_prime = max(0, min(255, r)) / 255.0
    g_prime = max(0, min(255, g)) / 255.0
    b_prime = max(0, min(255, b)) / 255.0

    k = 1.0 - max(r_prime, g_prime, b_prime)
    if k >= 1.0:
        return (0.0, 0.0, 0.0, 100.0)

    c = (1.0 - r_prime - k) / (1.0 - k)
    m = (1.0 - g_prime - k) / (1.0 - k)
    y = (1.0 - b_prime - k) / (1.0 - k)

    return (
        round(c * 100, 1),
        round(m * 100, 1),
        round(y * 100, 1),
        round(k * 100, 1),
    )


def hex_to_cmyk(hex_color: str) -> tuple[float, float, float, float]:
    """Convert hex color string directly to CMYK."""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_cmyk(r, g, b)


def mm_to_pt(mm: float) -> float:
    """Convert millimeters to PostScript points (1pt = 1/72 inch)."""
    return mm * 2.834645669


def pt_to_mm(pt: float) -> float:
    """Convert PostScript points to millimeters."""
    return pt / 2.834645669
