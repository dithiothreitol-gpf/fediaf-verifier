"""EAN/barcode validation models."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


class EANResult(NullSafeBase):
    """Validation result for a single barcode."""

    barcode_number: str = Field(default="", description="Raw digits extracted")
    barcode_type: str = Field(
        default="unknown",
        description="'EAN-13', 'EAN-8', 'UPC-A', 'unknown'",
    )
    barcode_readable: bool = Field(
        default=True, description="Whether AI could read the barcode"
    )
    check_digit_valid: bool = False
    expected_check_digit: str = ""
    country_prefix: str = ""
    country_name: str = ""
    notes: str = ""


class QRCodeResult(NullSafeBase):
    """Information about a QR code found on the label."""

    present: bool = False
    readable: bool = False
    content: str = Field(default="", description="URL or text if readable")
    notes: str = ""


class EANCheckReport(NullSafeBase):
    """AI output for barcode extraction + Python validation results."""

    ean_results: list[EANResult] = Field(default_factory=list)
    qr_codes: list[QRCodeResult] = Field(default_factory=list)
    barcodes_found: int = 0
    all_valid: bool = False
    summary: str = ""


class EANCheckResult(NullSafeBase):
    """Pipeline result wrapping EANCheckReport + error handling."""

    performed: bool = False
    report: EANCheckReport | None = None
    error: str | None = None
