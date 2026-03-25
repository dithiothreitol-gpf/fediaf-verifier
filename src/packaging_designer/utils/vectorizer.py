"""Raster-to-vector conversion wrapper.

Supports vtracer (primary) with Potrace fallback.
All converters output SVG strings.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from loguru import logger


def vectorize_image(
    image_bytes: bytes,
    colormode: str = "color",
    preset: str = "poster",
    filter_speckle: int = 4,
    color_precision: int = 6,
    corner_threshold: int = 60,
    segment_length: float = 4.0,
) -> str | None:
    """Convert raster image to SVG using vtracer.

    Args:
        image_bytes: PNG/JPG image bytes.
        colormode: 'color' or 'binary'.
        preset: 'bw', 'poster', or 'photo'.
        filter_speckle: Speckle filter (smaller = more detail).
        color_precision: Color quantization bits (1-8).
        corner_threshold: Corner detection threshold.
        segment_length: Max segment length.

    Returns:
        SVG string or None if vtracer is not available.
    """
    try:
        import vtracer

        svg = vtracer.convert_raw_image_to_svg(
            image_bytes,
            img_format="png",
            colormode=colormode,
            preset=preset,
            filter_speckle=filter_speckle,
            color_precision=color_precision,
            corner_threshold=corner_threshold,
            segment_length=segment_length,
        )
        logger.info(f"Vectorized with vtracer: {len(svg)} chars SVG")
        return svg
    except ImportError:
        logger.warning("vtracer not installed, trying fallback")
    except Exception as e:
        logger.warning(f"vtracer failed: {e}, trying fallback")

    # Fallback: try Potrace via subprocess (binary mode only)
    return _vectorize_potrace(image_bytes)


def _vectorize_potrace(image_bytes: bytes) -> str | None:
    """Fallback vectorization using Potrace via Pillow + subprocess."""
    try:
        import subprocess
        import tempfile

        from PIL import Image

        # Convert to BMP (Potrace input format)
        img = Image.open(BytesIO(image_bytes)).convert("L")
        img = img.point(lambda x: 0 if x < 128 else 255, "1")

        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as bmp_f:
            img.save(bmp_f.name, "BMP")
            bmp_path = bmp_f.name

        svg_path = bmp_path.replace(".bmp", ".svg")

        result = subprocess.run(
            ["potrace", bmp_path, "-s", "-o", svg_path],
            capture_output=True,
            timeout=30,
        )

        if result.returncode == 0 and Path(svg_path).exists():
            svg = Path(svg_path).read_text(encoding="utf-8")
            logger.info(f"Vectorized with Potrace fallback: {len(svg)} chars")
            Path(bmp_path).unlink(missing_ok=True)
            Path(svg_path).unlink(missing_ok=True)
            return svg

    except FileNotFoundError:
        logger.warning("Potrace not installed")
    except Exception as e:
        logger.warning(f"Potrace fallback failed: {e}")

    return None


def remove_background(image_bytes: bytes) -> bytes | None:
    """Remove background from image using rembg.

    Returns:
        PNG bytes with transparent background, or None if rembg unavailable.
    """
    try:
        from rembg import remove

        result = remove(image_bytes)
        logger.info(f"Background removed: {len(result)} bytes")
        return result
    except ImportError:
        logger.warning("rembg not installed \u2014 pip install rembg")
    except Exception as e:
        logger.warning(f"rembg failed: {e}")
    return None
