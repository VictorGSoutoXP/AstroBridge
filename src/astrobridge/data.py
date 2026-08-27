from __future__ import annotations

import astropy.units as u
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
    query = f"""
    SELECT TOP {int(limit)}
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
    """

    job = Gaia.launch_job_async(query)
    return job.get_results().to_pandas()


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

    numeric_ids = pd.to_numeric(pd.Series(source_ids, dtype="object"), errors="raise")
    if numeric_ids.empty:
        return pd.DataFrame(columns=GAIA_ALLWISE_REFERENCE_COLUMNS)
    if numeric_ids.isna().any() or (numeric_ids < 0).any():
        raise ValueError("source_ids must contain non-negative integers")

    unique_ids = list(dict.fromkeys(int(value) for value in numeric_ids))
    frames: list[pd.DataFrame] = []
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
        result = Gaia.launch_job_async(query).get_results().to_pandas()
        frames.append(result)

    if not frames:
        return pd.DataFrame(columns=GAIA_ALLWISE_REFERENCE_COLUMNS)
    reference = pd.concat(frames, ignore_index=True)
    return reference.loc[:, GAIA_ALLWISE_REFERENCE_COLUMNS]
