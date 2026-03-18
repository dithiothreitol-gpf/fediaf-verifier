"""Custom exception hierarchy for fediaf-verifier."""


class FediafVerifierError(Exception):
    """Base exception for all fediaf-verifier errors."""


class ConfigurationError(FediafVerifierError):
    """Missing or invalid configuration (API key, PDF path, etc.)."""


class PDFNotFoundError(ConfigurationError):
    """FEDIAF guidelines PDF not found at configured path."""


class ConversionError(FediafVerifierError):
    """File format conversion failed."""


class UnsupportedFormatError(ConversionError):
    """File format not supported."""


class LibreOfficeNotFoundError(ConversionError):
    """LibreOffice not installed (needed for DOCX conversion)."""


class APIError(FediafVerifierError):
    """AI provider API call failed."""


class CrossCheckError(APIError):
    """Cross-check API call failed (non-blocking)."""
