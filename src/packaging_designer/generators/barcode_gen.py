"""EAN-13 barcode generator — outputs SVG string."""

from __future__ import annotations

from io import BytesIO


def generate_ean13_svg(
    number: str,
    module_width: float = 0.33,
    module_height: float = 15.0,
    quiet_zone: float = 6.5,
    font_size: int = 10,
    text_distance: float = 5.0,
) -> str:
    """Generate an EAN-13 barcode as SVG string.

    Args:
        number: 12 or 13 digit EAN number (check digit auto-calculated if 12).
        module_width: Width of a single bar in mm.
        module_height: Height of bars in mm.
        quiet_zone: Quiet zone width in mm.
        font_size: Font size for number display.
        text_distance: Distance from bars to text in mm.

    Returns:
        SVG string of the barcode.
    """
    from barcode import EAN13
    from barcode.writer import SVGWriter

    number = number.strip().replace(" ", "")

    writer = SVGWriter()
    ean = EAN13(number, writer=writer)

    buf = BytesIO()
    ean.write(
        buf,
        options={
            "module_width": module_width,
            "module_height": module_height,
            "quiet_zone": quiet_zone,
            "font_size": font_size,
            "text_distance": text_distance,
        },
    )
    return buf.getvalue().decode("utf-8")
