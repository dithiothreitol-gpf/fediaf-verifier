"""File format conversion for label images and FEDIAF PDF."""

import base64
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

from fediaf_verifier.exceptions import (
    LibreOfficeNotFoundError,
    PDFNotFoundError,
    UnsupportedFormatError,
)


# Maximum base64 size before compression (~20MB raw = ~27MB base64)
_MAX_B64_SIZE = 20 * 1024 * 1024


def _compress_image(file_bytes: bytes, max_size: int = _MAX_B64_SIZE) -> tuple[bytes, str]:
    """Compress image if too large. Returns (bytes, media_type)."""
    if len(file_bytes) <= max_size:
        return file_bytes, ""

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(file_bytes))

        # Resize if very large (>4000px on any side)
        max_dim = 4000
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            logger.info("Image resized: {} -> {}", img.size, new_size)

        # Save as JPEG with quality reduction
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=85, optimize=True)
        compressed = buf.getvalue()
        logger.info(
            "Image compressed: {:.1f}MB -> {:.1f}MB",
            len(file_bytes) / 1_048_576,
            len(compressed) / 1_048_576,
        )
        return compressed, "image/jpeg"
    except Exception as e:
        logger.warning("Image compression failed: {}", e)
        return file_bytes, ""


def _detect_format(file_bytes: bytes) -> str | None:
    """Detect image/PDF format from magic bytes. Returns extension or None."""
    if len(file_bytes) < 8:
        return None
    header = file_bytes[:8]
    if header[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if header[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return ".webp"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if header[:5] == b"%PDF-":
        return ".pdf"
    if header[:4] == b"BM\x00\x00" or header[:2] == b"BM":
        return ".bmp"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tiff"
    return None


def file_to_base64(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """Convert a label file to base64.

    Compresses large images automatically. For PDFs over the size limit,
    logs a warning (API may reject).

    Args:
        file_bytes: Raw file bytes.
        filename: Original filename (used to detect format by extension).

    Returns:
        Tuple of (base64_string, media_type).

    Raises:
        UnsupportedFormatError: If file format is not supported.
        LibreOfficeNotFoundError: If DOCX conversion requires LibreOffice.
    """
    suffix = Path(filename).suffix.lower()

    if suffix in (".jpg", ".jpeg"):
        compressed, new_type = _compress_image(file_bytes)
        media = new_type or "image/jpeg"
        return base64.b64encode(compressed).decode(), media

    if suffix == ".png":
        compressed, new_type = _compress_image(file_bytes)
        media = new_type or "image/png"
        return base64.b64encode(compressed).decode(), media

    if suffix == ".webp":
        return base64.b64encode(file_bytes).decode(), "image/webp"

    if suffix == ".gif":
        return base64.b64encode(file_bytes).decode(), "image/gif"

    if suffix in (".bmp", ".tiff", ".tif"):
        # Convert BMP/TIFF to PNG via Pillow (APIs don't accept these natively)
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(file_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            logger.info("Converted {} to PNG", suffix)
            return base64.b64encode(buf.getvalue()).decode(), "image/png"
        except Exception as e:
            raise UnsupportedFormatError(
                f"Nie udalo sie skonwertowac pliku {suffix} do PNG: {e}"
            ) from e

    if suffix == ".pdf":
        size_mb = len(file_bytes) / 1_048_576
        if size_mb > 25:
            logger.warning(
                "PDF is very large ({:.1f}MB) — API may reject. "
                "Consider using a smaller file or single-page export.",
                size_mb,
            )
        return base64.b64encode(file_bytes).decode(), "application/pdf"

    if suffix == ".docx":
        return _docx_to_base64(file_bytes)

    # Fallback: detect format from file content (magic bytes)
    detected = _detect_format(file_bytes)
    if detected:
        logger.info("Extension {!r} unknown, detected format from content: {}", suffix, detected)
        return file_to_base64(file_bytes, f"detected{detected}")

    raise UnsupportedFormatError(
        f"Nieobslugiwany format pliku: {suffix}. "
        "Uzyj JPG, PNG, PDF lub DOCX."
    )


def _find_libreoffice() -> str:
    """Find LibreOffice executable on the system."""
    # Check PATH first
    for cmd in ("libreoffice", "soffice"):
        path = shutil.which(cmd)
        if path:
            return path

    # Check common Windows install locations
    windows_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in windows_paths:
        if os.path.isfile(p):
            return p

    raise LibreOfficeNotFoundError(
        "LibreOffice jest wymagany do konwersji plikow DOCX, ale nie zostal znaleziony.\n"
        "Zainstaluj LibreOffice: https://www.libreoffice.org/\n"
        "Na Windows: winget install LibreOffice\n"
        "Alternatywnie: skonwertuj plik DOCX do JPG/PNG/PDF przed wgraniem."
    )


def _docx_to_base64(docx_bytes: bytes) -> tuple[str, str]:
    """Convert DOCX -> PDF (via LibreOffice) -> PNG (first page)."""
    lo_path = _find_libreoffice()

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "label.docx")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        logger.info("Converting DOCX to PDF via LibreOffice...")
        try:
            subprocess.run(
                [
                    lo_path,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmpdir,
                    docx_path,
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as e:
            raise LibreOfficeNotFoundError(
                "Konwersja DOCX przekroczyla limit czasu (60s). "
                "Skonwertuj plik recznie do JPG/PNG/PDF."
            ) from e
        except subprocess.CalledProcessError as e:
            raise LibreOfficeNotFoundError(
                f"LibreOffice nie mogl skonwertowac pliku: {e.stderr.decode(errors='replace')}"
            ) from e

        pdf_path = os.path.join(tmpdir, "label.pdf")
        if not os.path.isfile(pdf_path):
            raise LibreOfficeNotFoundError(
                "LibreOffice nie wygenerowal pliku PDF. "
                "Skonwertuj plik recznie do JPG/PNG/PDF."
            )

        # Try converting PDF to PNG (requires pdf2image + poppler)
        try:
            from pdf2image import convert_from_path

            pages = convert_from_path(pdf_path, dpi=200)
            if not pages:
                # Fallback: return PDF directly
                with open(pdf_path, "rb") as f:
                    return base64.b64encode(f.read()).decode(), "application/pdf"

            img_buffer = io.BytesIO()
            pages[0].save(img_buffer, format="PNG")
            img_buffer.seek(0)
            logger.info("DOCX converted to PNG successfully")
            return base64.b64encode(img_buffer.read()).decode(), "image/png"

        except ImportError:
            # pdf2image not installed — return PDF directly (API supports it)
            logger.info("pdf2image not available, sending converted PDF directly to API")
            with open(pdf_path, "rb") as f:
                return base64.b64encode(f.read()).decode(), "application/pdf"


def load_pdf_base64(pdf_path: Path) -> str:
    """Load a PDF file as base64 string.

    Raises:
        PDFNotFoundError: If the file does not exist.
    """
    if not pdf_path.is_file():
        raise PDFNotFoundError(
            f"Nie znaleziono pliku: {pdf_path}\n"
            "Pobierz FEDIAF Nutritional Guidelines 2021 ze strony fediaf.org "
            "i zapisz w folderze data/."
        )

    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode()
