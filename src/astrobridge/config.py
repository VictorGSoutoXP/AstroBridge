from dataclasses import dataclass


@dataclass(frozen=True)
class FieldConfig:
    ra: float
    dec: float
    radius: float
    gaia_limit: int = 20000
    match_threshold_arcsec: float = 2.0
    gaia_epoch: float = 2016.0
    wise_epoch: float = 2010.5
