"""Cross-check result models (internal, not AI output)."""

from pydantic import BaseModel


class Discrepancy(BaseModel):
    """A discrepancy between main and cross-check nutrient readings."""

    nutrient: str
    main_value: float
    cross_value: float
    difference: float


class CrossCheckResult(BaseModel):
    """Result of the cross-validation (Layer 2)."""

    passed: bool | None = None  # None = not executed
    discrepancies: list[Discrepancy] = []
    cross_check_values: dict[str, float | None] = {}
    reading_notes: str = ""
    error: str | None = None
