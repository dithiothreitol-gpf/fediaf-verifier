"""Product identification models and enums."""

from enum import StrEnum

from pydantic import BaseModel


class Species(StrEnum):
    DOG = "dog"
    CAT = "cat"
    OTHER = "other"
    UNKNOWN = "unknown"


class Lifestage(StrEnum):
    PUPPY = "puppy"
    KITTEN = "kitten"
    ADULT = "adult"
    SENIOR = "senior"
    ALL_STAGES = "all_stages"
    UNKNOWN = "unknown"


class FoodType(StrEnum):
    DRY = "dry"
    WET = "wet"
    SEMI_MOIST = "semi_moist"
    TREAT = "treat"
    SUPPLEMENT = "supplement"
    UNKNOWN = "unknown"


class Product(BaseModel):
    """Product identification extracted from label."""

    name: str | None = None
    brand: str | None = None
    species: Species
    lifestage: Lifestage
    food_type: FoodType
    net_weight: str | None = None
