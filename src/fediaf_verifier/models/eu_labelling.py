"""EU Regulation 767/2009 labelling check model."""

from pydantic import BaseModel


class EULabellingCheck(BaseModel):
    """EU labelling requirements check (Regulation 767/2009)."""

    ingredients_listed: bool
    analytical_constituents_present: bool
    manufacturer_info: bool
    net_weight_declared: bool
    species_clearly_stated: bool
    batch_or_date_present: bool
