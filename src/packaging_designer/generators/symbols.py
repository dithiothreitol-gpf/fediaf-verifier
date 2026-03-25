"""Packaging regulatory symbols loader and generator.

Loads pre-built SVG symbols from assets/symbols/ directory.
"""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "symbols"

# Registry of available symbols
SYMBOL_REGISTRY: dict[str, dict] = {
    "recycling_mobius": {
        "file": "mobius_loop.svg",
        "display_name": "Mobius Loop (recykling)",
        "default_size_mm": 12,
    },
    "recycling_tidyman": {
        "file": "tidyman.svg",
        "display_name": "Tidyman",
        "default_size_mm": 10,
    },
    "recycling_pao": {
        "file": "pao_12m.svg",
        "display_name": "PAO (okres po otwarciu)",
        "default_size_mm": 10,
    },
    "recycling_green_dot": {
        "file": "green_dot.svg",
        "display_name": "Green Dot (Zielony Punkt)",
        "default_size_mm": 10,
    },
    "ce_mark": {
        "file": "ce_mark.svg",
        "display_name": "Znak CE",
        "default_size_mm": 8,
    },
    "triman": {
        "file": "triman.svg",
        "display_name": "Triman (Francja)",
        "default_size_mm": 10,
    },
}


def get_available_symbols() -> list[dict]:
    """Return list of available symbols with metadata."""
    result = []
    for symbol_id, meta in SYMBOL_REGISTRY.items():
        svg_path = ASSETS_DIR / meta["file"]
        result.append(
            {
                "id": symbol_id,
                "display_name": meta["display_name"],
                "available": svg_path.exists(),
                "default_size_mm": meta["default_size_mm"],
            }
        )
    return result


def load_symbol_svg(symbol_id: str) -> str | None:
    """Load SVG content for a symbol by ID."""
    if symbol_id not in SYMBOL_REGISTRY:
        return None
    svg_path = ASSETS_DIR / SYMBOL_REGISTRY[symbol_id]["file"]
    if not svg_path.exists():
        return None
    return svg_path.read_text(encoding="utf-8")


def get_symbol_size_mm(symbol_id: str) -> float:
    """Get default size in mm for a symbol."""
    if symbol_id in SYMBOL_REGISTRY:
        return SYMBOL_REGISTRY[symbol_id]["default_size_mm"]
    return 10
