"""Nutrient value models."""

from pydantic import BaseModel, Field


class NutrientValues(BaseModel):
    """Nutrient values extracted from label, in % as-fed."""

    crude_protein: float | None = None
    crude_fat: float | None = None
    crude_fibre: float | None = None
    moisture: float | None = None
    crude_ash: float | None = None
    calcium: float | None = None
    phosphorus: float | None = None


class NutrientsOnly(BaseModel):
    """Simplified model for cross-check (Layer 2). Only numeric values + reading notes."""

    crude_protein: float | None = None
    crude_fat: float | None = None
    crude_fibre: float | None = None
    moisture: float | None = None
    crude_ash: float | None = None
    calcium: float | None = None
    phosphorus: float | None = None
    reading_notes: str = Field(
        default="",
        description=(
            "Notes about reading quality, e.g. "
            "'all values clear' or 'digit near fat value could be 8 or 6'"
        ),
    )


# Fields to iterate over when comparing nutrients
NUTRIENT_FIELDS: list[str] = [
    "crude_protein",
    "crude_fat",
    "crude_fibre",
    "moisture",
    "crude_ash",
    "calcium",
    "phosphorus",
]
