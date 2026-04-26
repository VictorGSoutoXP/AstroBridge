from __future__ import annotations

import pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia
from astroquery.ipac.irsa import Irsa


def fetch_gaia_dr3(ra: float, dec: float, radius: float, limit: int = 20000) -> pd.DataFrame:
    query = f"""
    SELECT TOP {int(limit)}
        source_id,
        ra,
        dec,
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
