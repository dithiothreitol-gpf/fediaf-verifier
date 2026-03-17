"""Market trends models."""

from enum import StrEnum

from pydantic import BaseModel


class Positioning(StrEnum):
    TRENDY = "trendy"
    STANDARD = "standard"
    OUTDATED = "outdated"
    NICHE = "niche"


class MarketTrends(BaseModel):
    """Optional market trends analysis section."""

    country: str
    summary: str
    positioning: Positioning
    trend_notes: list[str] = []
