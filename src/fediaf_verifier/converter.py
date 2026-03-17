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


def file_to_base64(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """Convert a label file to base64.

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
        return base64.b64encode(file_bytes).decode(), "image/jpeg"

    if suffix == ".png":
        return base64.b64encode(file_bytes).decode(), "image/png"

    if suffix == ".webp":
        return base64.b64encode(file_bytes).decode(), "image/webp"

    if suffix == ".gif":
        return base64.b64encode(file_bytes).decode(), "image/gif"

    if suffix == ".pdf":
        return base64.b64encode(file_bytes).decode(), "application/pdf"

    if suffix == ".docx":
        return _docx_to_base64(file_bytes)

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
