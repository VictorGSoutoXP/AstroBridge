import pandas as pd
import numpy as np
from astroquery.gaia import Gaia
from astroquery.irsa import Irsa
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as u

ra = 83.633
dec = 22.0145
radius = 0.05

query_gaia = f"""
SELECT TOP 2000
    source_id, ra, dec, parallax, pmra, pmdec,
    phot_g_mean_mag, bp_rp
FROM gaiadr3.gaia_source
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    CIRCLE('ICRS', {ra}, {dec}, {radius})
)=1
"""

job = Gaia.launch_job(query_gaia)
gaia_df = job.get_results().to_pandas()

wise_df = Irsa.query_region(
    SkyCoord(ra, dec, unit=(u.deg, u.deg)),
    catalog="allwise_p3as_psd",
    spatial="Cone",
    radius=radius * u.deg
).to_pandas()

gaia_coords = SkyCoord(ra=gaia_df["ra"].values*u.deg, dec=gaia_df["dec"].values*u.deg)
wise_coords = SkyCoord(ra=wise_df["ra"].values*u.deg, dec=wise_df["dec"].values*u.deg)

idx, d2d, _ = gaia_coords.match_to_catalog_sky(wise_coords)

threshold = 2 * u.arcsec
match_mask = d2d < threshold

matches = pd.DataFrame({
    "gaia_id": gaia_df["source_id"][match_mask].values,
    "gaia_ra": gaia_df["ra"][match_mask].values,
    "gaia_dec": gaia_df["dec"][match_mask].values,
    "wise_ra": wise_df.iloc[idx[match_mask]]["ra"].values,
    "wise_dec": wise_df.iloc[idx[match_mask]]["dec"].values,
    "distance_arcsec": d2d[match_mask].arcsec
})

simbad = Simbad()
simbad.add_votable_fields("otype")

known = []

for _, row in matches.head(50).iterrows():
    result = simbad.query_region(
        SkyCoord(row["gaia_ra"], row["gaia_dec"], unit="deg"),
        radius="2s"
    )
    known.append(0 if result is None else 1)

matches["known_in_simbad"] = known

print("Total Gaia:", len(gaia_df))
print("Total WISE:", len(wise_df))
print("Matches:", len(matches))
print("Conhecidos:", matches["known_in_simbad"].sum())

matches.to_csv("astro_matches.csv", index=False)