from __future__ import annotations

import astropy.units as u
import pandas as pd
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad
from tqdm import tqdm


def add_simbad_flags(
    matches: pd.DataFrame,
    ra_col: str = "gaia_ra",
    dec_col: str = "gaia_dec",
    radius_arcsec: float = 2.0,
    limit: int | None = 100,
) -> pd.DataFrame:
    df = matches.copy()
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative or None")

    if df.empty:
        df["known_in_simbad"] = []
        df["simbad_main_id"] = []
        df["simbad_type"] = []
        df["simbad_query_status"] = []
        return df

    known = []
    main_ids = []
    object_types = []
    query_statuses = []

    try:
        simbad = Simbad()
        simbad.add_votable_fields("otype")
    except Exception:
        df["known_in_simbad"] = None
        df["simbad_main_id"] = None
        df["simbad_type"] = None
        df["simbad_query_status"] = "error"
        return df

    iterable = list(df.iterrows()) if limit is None else list(df.head(limit).iterrows())

    lookup = {}

    for idx, row in tqdm(iterable, total=len(iterable), desc="SIMBAD"):
        try:
            result = simbad.query_region(
                SkyCoord(float(row[ra_col]), float(row[dec_col]), unit="deg", frame="icrs"),
                radius=radius_arcsec * u.arcsec,
            )

            if result is None or len(result) == 0:
                lookup[idx] = (0, None, None, "no_match")
            else:
                main_id = str(result[0]["main_id"]) if "main_id" in result.colnames else None
                otype = str(result[0]["otype"]) if "otype" in result.colnames else None
                lookup[idx] = (1, main_id, otype, "matched")

        except Exception:
            lookup[idx] = (None, None, None, "error")

    for idx in df.index:
        value = lookup.get(idx, (None, None, None, "not_queried"))
        known.append(value[0])
        main_ids.append(value[1])
        object_types.append(value[2])
        query_statuses.append(value[3])

    df["known_in_simbad"] = known
    df["simbad_main_id"] = main_ids
    df["simbad_type"] = object_types
    df["simbad_query_status"] = query_statuses

    return df
