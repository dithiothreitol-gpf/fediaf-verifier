"""Coordinate transformation utilities for DTP output.

Conventions:
- AI Vision returns bounding boxes as [x, y, w, h] normalized 0-1000
  with origin at top-left, Y increasing downward.
- Illustrator uses points with origin at bottom-left, Y increasing upward.
- InDesign/IDML uses points with origin at top-left, Y increasing downward.
"""

from __future__ import annotations


def normalized_to_illustrator(
    bbox: list[float],
    artboard_width_pt: float,
    artboard_height_pt: float,
) -> tuple[float, float, float, float]:
    """Convert normalized 0-1000 bbox to Illustrator coordinates.

    Returns (x, y, width, height) in points with AI coordinate system
    (origin bottom-left, Y up).
    """
    nx, ny, nw, nh = bbox[0], bbox[1], bbox[2], bbox[3]

    x = (nx / 1000.0) * artboard_width_pt
    w = (nw / 1000.0) * artboard_width_pt
    h = (nh / 1000.0) * artboard_height_pt
    # Flip Y: AI origin is bottom-left
    y = artboard_height_pt - ((ny / 1000.0) * artboard_height_pt) - h

    return (x, y, w, h)


def normalized_to_idml(
    bbox: list[float],
    page_width_pt: float,
    page_height_pt: float,
) -> tuple[float, float, float, float]:
    """Convert normalized 0-1000 bbox to IDML coordinates.

    Returns (x, y, width, height) in points with IDML coordinate system
    (origin top-left, Y down — same as normalized).
    """
    nx, ny, nw, nh = bbox[0], bbox[1], bbox[2], bbox[3]

    x = (nx / 1000.0) * page_width_pt
    y = (ny / 1000.0) * page_height_pt
    w = (nw / 1000.0) * page_width_pt
    h = (nh / 1000.0) * page_height_pt

    return (x, y, w, h)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range."""
    return max(min_val, min(value, max_val))
