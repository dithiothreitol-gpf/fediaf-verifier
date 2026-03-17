"""Converter module tests using synthetic images."""

import base64
import io

import pytest
from PIL import Image

from fediaf_verifier.converter import file_to_base64
from fediaf_verifier.exceptions import UnsupportedFormatError


def _make_png_bytes() -> bytes:
    """Create a minimal 1x1 pixel PNG in memory."""
    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes() -> bytes:
    """Create a minimal 1x1 pixel JPEG in memory."""
    img = Image.new("RGB", (1, 1), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestFileToBase64:
    def test_png_returns_correct_media_type(self):
        b64, media_type = file_to_base64(_make_png_bytes(), "label.png")
        assert media_type == "image/png"
        # Verify it's valid base64
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0

    def test_jpeg_returns_correct_media_type(self):
        _, media_type = file_to_base64(_make_jpeg_bytes(), "label.jpg")
        assert media_type == "image/jpeg"

    def test_jpeg_extension_variant(self):
        _, media_type = file_to_base64(_make_jpeg_bytes(), "label.jpeg")
        assert media_type == "image/jpeg"

    def test_pdf_returns_correct_media_type(self):
        # Minimal PDF-like bytes (not a real PDF but tests the routing)
        pdf_bytes = b"%PDF-1.4 fake content"
        _, media_type = file_to_base64(pdf_bytes, "label.pdf")
        assert media_type == "application/pdf"

    def test_unsupported_format_raises(self):
        with pytest.raises(UnsupportedFormatError, match="Nieobslugiwany format"):
            file_to_base64(b"some data", "label.bmp")

    def test_unsupported_format_txt(self):
        with pytest.raises(UnsupportedFormatError):
            file_to_base64(b"some text", "label.txt")

    def test_case_insensitive_extension(self):
        _, media_type = file_to_base64(_make_png_bytes(), "LABEL.PNG")
        assert media_type == "image/png"

    def test_webp_supported(self):
        img = Image.new("RGB", (1, 1), color="green")
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        _, media_type = file_to_base64(buf.getvalue(), "label.webp")
        assert media_type == "image/webp"

    def test_roundtrip_png(self):
        """Encode and decode should produce the same bytes."""
        original = _make_png_bytes()
        b64, _ = file_to_base64(original, "test.png")
        decoded = base64.b64decode(b64)
        assert decoded == original
