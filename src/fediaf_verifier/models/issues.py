"""Issue and severity models."""

from enum import StrEnum

from pydantic import BaseModel


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class Issue(BaseModel):
    """A regulatory issue found during verification."""

    severity: Severity
    code: str  # e.g. "PROTEIN_BELOW_MIN"
    description: str
    fediaf_reference: str | None = None  # e.g. "Table 11, section 3.2"
    found_value: float | str | None = None
    required_value: str | None = None
    source: str | None = None  # "AI" or "HARD_RULE" — set by pipeline, not AI
