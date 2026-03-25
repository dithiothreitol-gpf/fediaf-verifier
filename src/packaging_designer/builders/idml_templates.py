"""IDML layout templates per packaging type.

Defines preset text frame layouts for common packaging types.
Each template specifies where regulatory sections should be placed
on the back label.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FrameSlot:
    """A text frame slot in the template layout.

    Position and size as fractions of page (0.0-1.0).
    """

    section_id: str
    label: str
    x_frac: float  # left edge as fraction of page width
    y_frac: float  # top edge as fraction of page height
    w_frac: float  # width as fraction
    h_frac: float  # height as fraction
    font_size: float = 8
    bold: bool = False


@dataclass
class PackagingTemplate:
    """Layout template for a packaging type."""

    name: str
    description: str
    frames: list[FrameSlot] = field(default_factory=list)


# -- Templates ----------------------------------------------------------------

TEMPLATE_POUCH_BACK = PackagingTemplate(
    name="pouch_back",
    description="Tylna strona saszetki/stand-up pouch",
    frames=[
        FrameSlot("product_name", "Nazwa produktu", 0.05, 0.03, 0.9, 0.06, font_size=14, bold=True),
        FrameSlot("composition", "Sk\u0142ad", 0.05, 0.11, 0.9, 0.18, font_size=7),
        FrameSlot("analytical_constituents", "Sk\u0142adniki analityczne", 0.05, 0.31, 0.45, 0.15, font_size=7),
        FrameSlot("additives", "Dodatki", 0.52, 0.31, 0.43, 0.15, font_size=7),
        FrameSlot("feeding_guidelines", "Zalecenia \u017cywieniowe", 0.05, 0.48, 0.9, 0.2, font_size=7),
        FrameSlot("storage", "Przechowywanie", 0.05, 0.70, 0.9, 0.06, font_size=6.5),
        FrameSlot("manufacturer", "Producent", 0.05, 0.78, 0.55, 0.1, font_size=6.5),
        FrameSlot("best_before", "Data wa\u017cno\u015bci", 0.05, 0.90, 0.4, 0.04, font_size=7),
        FrameSlot("lot", "LOT", 0.05, 0.94, 0.4, 0.04, font_size=7),
        FrameSlot("barcode_area", "Kod EAN", 0.62, 0.78, 0.33, 0.18, font_size=7),
    ],
)

TEMPLATE_BOX_BACK = PackagingTemplate(
    name="box_back",
    description="Tylna strona pude\u0142ka kartonowego",
    frames=[
        FrameSlot("product_name", "Nazwa produktu", 0.05, 0.03, 0.9, 0.05, font_size=12, bold=True),
        FrameSlot("composition", "Sk\u0142ad", 0.05, 0.10, 0.9, 0.15, font_size=7),
        FrameSlot("analytical_constituents", "Sk\u0142adniki analityczne", 0.05, 0.27, 0.43, 0.15, font_size=7),
        FrameSlot("additives", "Dodatki", 0.52, 0.27, 0.43, 0.15, font_size=7),
        FrameSlot("feeding_guidelines", "Zalecenia \u017cywieniowe", 0.05, 0.44, 0.9, 0.22, font_size=7),
        FrameSlot("storage", "Przechowywanie", 0.05, 0.68, 0.9, 0.05, font_size=6.5),
        FrameSlot("manufacturer", "Producent", 0.05, 0.75, 0.55, 0.1, font_size=6.5),
        FrameSlot("best_before", "Data wa\u017cno\u015bci", 0.05, 0.87, 0.4, 0.04, font_size=7),
        FrameSlot("lot", "LOT", 0.05, 0.92, 0.4, 0.04, font_size=7),
        FrameSlot("barcode_area", "Kod EAN", 0.60, 0.80, 0.35, 0.16, font_size=7),
    ],
)

TEMPLATE_CAN_LABEL = PackagingTemplate(
    name="can_label",
    description="Etykieta puszki (wrap-around)",
    frames=[
        FrameSlot("product_name", "Nazwa produktu", 0.03, 0.03, 0.94, 0.06, font_size=11, bold=True),
        FrameSlot("composition", "Sk\u0142ad", 0.03, 0.11, 0.94, 0.2, font_size=6.5),
        FrameSlot("analytical_constituents", "Sk\u0142adniki analityczne", 0.03, 0.33, 0.45, 0.15, font_size=6.5),
        FrameSlot("additives", "Dodatki", 0.52, 0.33, 0.45, 0.15, font_size=6.5),
        FrameSlot("feeding_guidelines", "Zalecenia", 0.03, 0.50, 0.94, 0.18, font_size=6),
        FrameSlot("storage", "Przechowywanie", 0.03, 0.70, 0.94, 0.05, font_size=6),
        FrameSlot("manufacturer", "Producent", 0.03, 0.77, 0.5, 0.1, font_size=6),
        FrameSlot("best_before", "Data", 0.03, 0.89, 0.35, 0.04, font_size=6),
        FrameSlot("lot", "LOT", 0.03, 0.93, 0.35, 0.04, font_size=6),
        FrameSlot("barcode_area", "EAN", 0.58, 0.80, 0.38, 0.16, font_size=6),
    ],
)

TEMPLATE_GENERIC = PackagingTemplate(
    name="generic",
    description="Uniwersalny szablon tylnej strony",
    frames=[
        FrameSlot("product_name", "Nazwa", 0.05, 0.03, 0.9, 0.06, font_size=12, bold=True),
        FrameSlot("composition", "Sk\u0142ad", 0.05, 0.11, 0.9, 0.2, font_size=7),
        FrameSlot("analytical_constituents", "Sk\u0142adniki", 0.05, 0.33, 0.9, 0.12, font_size=7),
        FrameSlot("feeding_guidelines", "Zalecenia", 0.05, 0.47, 0.9, 0.18, font_size=7),
        FrameSlot("manufacturer", "Producent", 0.05, 0.68, 0.9, 0.1, font_size=7),
        FrameSlot("best_before", "Data", 0.05, 0.82, 0.4, 0.04, font_size=7),
        FrameSlot("lot", "LOT", 0.05, 0.87, 0.4, 0.04, font_size=7),
        FrameSlot("barcode_area", "EAN", 0.55, 0.78, 0.4, 0.18, font_size=7),
    ],
)


def get_template(package_type: str) -> PackagingTemplate:
    """Get layout template for a packaging type."""
    mapping = {
        "pouch": TEMPLATE_POUCH_BACK,
        "standup_pouch": TEMPLATE_POUCH_BACK,
        "sachet": TEMPLATE_POUCH_BACK,
        "box": TEMPLATE_BOX_BACK,
        "tray": TEMPLATE_BOX_BACK,
        "can": TEMPLATE_CAN_LABEL,
        "bottle": TEMPLATE_CAN_LABEL,
        "tube": TEMPLATE_CAN_LABEL,
    }
    return mapping.get(package_type, TEMPLATE_GENERIC)
