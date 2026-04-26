from __future__ import annotations

import numpy as np
import pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord


def propagate_gaia_position(
    gaia_df: pd.DataFrame,
    from_epoch: float = 2016.0,
    to_epoch: float = 2010.5,
) -> pd.DataFrame:
    df = gaia_df.copy()
    dt = float(to_epoch) - float(from_epoch)

    pmra = df["pmra"].fillna(0).astype(float).to_numpy()
    pmdec = df["pmdec"].fillna(0).astype(float).to_numpy()
    ra = df["ra"].astype(float).to_numpy()
    dec = df["dec"].astype(float).to_numpy()

    cos_dec = np.cos(np.deg2rad(dec))
    cos_dec = np.where(np.abs(cos_dec) < 1e-12, np.nan, cos_dec)

    df["ra_epoch"] = ra + (pmra / 3.6e6) * dt / cos_dec
    df["dec_epoch"] = dec + (pmdec / 3.6e6) * dt

    return df


def crossmatch_nearest(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_ra: str = "ra",
    left_dec: str = "dec",
    right_ra: str = "ra",
    right_dec: str = "dec",
    threshold_arcsec: float = 2.0,
) -> pd.DataFrame:
    if left_df.empty or right_df.empty:
        return pd.DataFrame()

    left_coords = SkyCoord(
        ra=left_df[left_ra].astype(float).to_numpy() * u.deg,
        dec=left_df[left_dec].astype(float).to_numpy() * u.deg,
        frame="icrs",
    )

    right_coords = SkyCoord(
        ra=right_df[right_ra].astype(float).to_numpy() * u.deg,
        dec=right_df[right_dec].astype(float).to_numpy() * u.deg,
        frame="icrs",
    )

    idx, d2d, _ = left_coords.match_to_catalog_sky(right_coords)
    mask = d2d.arcsec < float(threshold_arcsec)

    left_match = left_df.loc[mask].reset_index(drop=True)
    right_match = right_df.iloc[idx[mask]].reset_index(drop=True)

    left_match = left_match.add_prefix("gaia_")
    right_match = right_match.add_prefix("wise_")

    result = pd.concat([left_match, right_match], axis=1)
    result["distance_arcsec"] = d2d.arcsec[mask]

    return result
