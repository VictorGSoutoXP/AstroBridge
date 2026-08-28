from __future__ import annotations

import re
from numbers import Integral

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia
from astroquery.ipac.irsa import Irsa

GAIA_ALLWISE_REFERENCE_COLUMNS = [
    "source_id",
    "original_ext_source_id",
    "angular_distance",
    "xm_flag",
    "allwise_oid",
    "number_of_neighbours",
    "number_of_mates",
]


def fetch_gaia_dr3(ra: float, dec: float, radius: float, limit: int = 20000) -> pd.DataFrame:
    if isinstance(limit, (bool, np.bool_)) or not isinstance(limit, Integral) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    limit = int(limit)
    query_limit = limit + 1
    query = f"""
    SELECT TOP {query_limit}
        source_id,
        ra,
        ra_error,
        dec,
        dec_error,
        parallax,
        parallax_error,
        pmra,
        pmra_error,
        pmdec,
        pmdec_error,
        phot_g_mean_mag,
        phot_bp_mean_mag,
        phot_rp_mean_mag,
        bp_rp,
        ruwe
    FROM gaiadr3.gaia_source
    WHERE CONTAINS(
        POINT('ICRS', ra, dec),
        CIRCLE('ICRS', {float(ra)}, {float(dec)}, {float(radius)})
    ) = 1
    ORDER BY source_id
    """

    job = Gaia.launch_job_async(query)
    retrieved = job.get_results().to_pandas()
    result = retrieved.iloc[:limit].copy()
    result.attrs["gaia_query_limit_reached"] = len(retrieved) > limit
    result.attrs["adql_query"] = query.strip()
    return result


def fetch_allwise(ra: float, dec: float, radius: float) -> pd.DataFrame:
    result = Irsa.query_region(
        SkyCoord(ra, dec, unit=(u.deg, u.deg), frame="icrs"),
        catalog="allwise_p3as_psd",
        spatial="Cone",
        radius=radius * u.deg,
    )

    df = result.to_pandas()

    keep = [
        "designation",
        "ra",
        "dec",
        "sigra",
        "sigdec",
        "w1mpro",
        "w1sigmpro",
        "w2mpro",
        "w2sigmpro",
        "w3mpro",
        "w3sigmpro",
        "w4mpro",
        "w4sigmpro",
        "cc_flags",
        "ph_qual",
    ]

    available = [col for col in keep if col in df.columns]
    return df[available].copy()


def fetch_gaia_allwise_best_neighbours(
    source_ids: pd.Series | list[int],
    *,
    chunk_size: int = 1000,
) -> pd.DataFrame:
    """Fetch official Gaia DR3-AllWISE best neighbours for specific Gaia sources."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    raw_ids = list(source_ids)
    if not raw_ids:
        return pd.DataFrame(columns=GAIA_ALLWISE_REFERENCE_COLUMNS)

    normalized_ids: list[int] = []
    max_source_id = int(np.iinfo(np.int64).max)
    for value in raw_ids:
        if isinstance(value, (bool, np.bool_)) or isinstance(value, (float, np.floating)):
            raise ValueError("source_ids must contain exact non-negative integers, not floats")
        if isinstance(value, Integral):
            source_id = int(value)
        elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
            source_id = int(value.strip())
        else:
            raise ValueError("source_ids must contain exact non-negative integers")
        if not 0 <= source_id <= max_source_id:
            raise ValueError("source_ids must fit in a signed 64-bit integer")
        normalized_ids.append(source_id)

    unique_ids = list(dict.fromkeys(normalized_ids))
    frames: list[pd.DataFrame] = []
    queries: list[str] = []
    selected_columns = ",\n        ".join(GAIA_ALLWISE_REFERENCE_COLUMNS)
    for start in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[start : start + chunk_size]
        identifiers = ", ".join(str(value) for value in chunk)
        query = f"""
        SELECT
            {selected_columns}
        FROM gaiadr3.allwise_best_neighbour
        WHERE source_id IN ({identifiers})
        """
        queries.append(query.strip())
        result = Gaia.launch_job_async(query).get_results().to_pandas()
        frames.append(result)

    if not frames:
        return pd.DataFrame(columns=GAIA_ALLWISE_REFERENCE_COLUMNS)
    reference = pd.concat(frames, ignore_index=True)
    reference = reference.loc[:, GAIA_ALLWISE_REFERENCE_COLUMNS]
    reference.attrs["adql_queries"] = queries
    return reference
