from __future__ import annotations

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord, search_around_sky


def _separation_from_center_deg(
    catalog: pd.DataFrame,
    center_ra_deg: float,
    center_dec_deg: float,
    *,
    ra_col: str,
    dec_col: str,
) -> np.ndarray:
    """Return center separations in degrees, preserving invalid rows as NaN."""

    if not np.isfinite(center_ra_deg) or not 0.0 <= center_ra_deg < 360.0:
        raise ValueError("center_ra_deg must be in the interval [0, 360)")
    if not np.isfinite(center_dec_deg) or not -90.0 <= center_dec_deg <= 90.0:
        raise ValueError("center_dec_deg must be in the interval [-90, 90]")
    if ra_col not in catalog or dec_col not in catalog:
        raise ValueError(f"catalog must contain {ra_col!r} and {dec_col!r}")

    ra = pd.to_numeric(catalog[ra_col], errors="coerce").to_numpy(dtype=float)
    dec = pd.to_numeric(catalog[dec_col], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(ra) & np.isfinite(dec) & (dec >= -90.0) & (dec <= 90.0)
    separations = np.full(len(catalog), np.nan, dtype=float)
    if valid.any():
        center = SkyCoord(center_ra_deg * u.deg, center_dec_deg * u.deg, frame="icrs")
        coordinates = SkyCoord(ra[valid] * u.deg, dec[valid] * u.deg, frame="icrs")
        separations[valid] = center.separation(coordinates).deg
    return separations


def count_rows_within_cone(
    catalog: pd.DataFrame,
    center_ra_deg: float,
    center_dec_deg: float,
    radius_deg: float,
    *,
    ra_col: str = "ra",
    dec_col: str = "dec",
) -> int:
    """Count finite catalog coordinates inside a spherical cone."""

    if not np.isfinite(radius_deg) or not 0.0 < radius_deg <= 180.0:
        raise ValueError("radius_deg must be in the interval (0, 180]")
    separations = _separation_from_center_deg(
        catalog,
        center_ra_deg,
        center_dec_deg,
        ra_col=ra_col,
        dec_col=dec_col,
    )
    return int(np.count_nonzero(separations <= radius_deg))


def maximum_radius_from_center_deg(
    catalog: pd.DataFrame,
    center_ra_deg: float,
    center_dec_deg: float,
    *,
    ra_col: str = "ra",
    dec_col: str = "dec",
) -> float:
    """Return the largest finite catalog separation from a field center."""

    separations = _separation_from_center_deg(
        catalog,
        center_ra_deg,
        center_dec_deg,
        ra_col=ra_col,
        dec_col=dec_col,
    )
    finite = separations[np.isfinite(separations)]
    return float(finite.max()) if finite.size else 0.0


def propagate_gaia_position(
    gaia_df: pd.DataFrame,
    from_epoch: float = 2016.0,
    to_epoch: float = 2010.5,
    default_position_error_mas: float = 1.0,
    default_pm_error_mas_per_year: float = 1.0,
) -> pd.DataFrame:
    r"""Propagate Gaia positions and independent per-axis errors to a target epoch.

    Gaia ``pmra`` follows the :math:`\mu_{\alpha *}` convention and therefore
    includes the cosine-of-declination term. Correlations between the Gaia
    astrometric parameters are not yet included; the returned
    ``position_sigma_arcsec`` is an effective circular one-sigma uncertainty.
    """

    df = gaia_df.copy()
    dt = float(to_epoch) - float(from_epoch)

    pmra = df["pmra"].fillna(0).astype(float).to_numpy()
    pmdec = df["pmdec"].fillna(0).astype(float).to_numpy()
    ra = df["ra"].astype(float).to_numpy()
    dec = df["dec"].astype(float).to_numpy()

    cos_dec = np.cos(np.deg2rad(dec))
    cos_dec = np.where(np.abs(cos_dec) < 1e-12, np.nan, cos_dec)

    df["ra_epoch"] = (ra + (pmra / 3.6e6) * dt / cos_dec) % 360.0
    df["dec_epoch"] = dec + (pmdec / 3.6e6) * dt

    def error_values(column: str, default: float) -> np.ndarray:
        if column not in df:
            return np.full(len(df), default, dtype=float)
        values = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
        return np.where(np.isfinite(values) & (values >= 0), values, default)

    ra_error = error_values("ra_error", default_position_error_mas)
    dec_error = error_values("dec_error", default_position_error_mas)
    pmra_error = error_values("pmra_error", default_pm_error_mas_per_year)
    pmdec_error = error_values("pmdec_error", default_pm_error_mas_per_year)

    df["ra_sigma_epoch_arcsec"] = np.hypot(ra_error, dt * pmra_error) / 1000.0
    df["dec_sigma_epoch_arcsec"] = np.hypot(dec_error, dt * pmdec_error) / 1000.0
    df["position_sigma_arcsec"] = np.sqrt(
        (df["ra_sigma_epoch_arcsec"].to_numpy() ** 2 + df["dec_sigma_epoch_arcsec"].to_numpy() ** 2)
        / 2.0
    )
    df["proper_motion_available"] = df["pmra"].notna() & df["pmdec"].notna()

    return df


def effective_circular_sigma_arcsec(
    sigma_ra_arcsec: pd.Series | np.ndarray,
    sigma_dec_arcsec: pd.Series | np.ndarray,
    default_arcsec: float = 0.5,
    floor_arcsec: float = 1e-4,
) -> np.ndarray:
    """Reduce independent per-axis uncertainties to an effective circular sigma."""

    sigma_ra = np.asarray(sigma_ra_arcsec, dtype=float)
    sigma_dec = np.asarray(sigma_dec_arcsec, dtype=float)
    sigma_ra = np.where(np.isfinite(sigma_ra) & (sigma_ra > 0), sigma_ra, default_arcsec)
    sigma_dec = np.where(np.isfinite(sigma_dec) & (sigma_dec > 0), sigma_dec, default_arcsec)
    sigma = np.sqrt((sigma_ra**2 + sigma_dec**2) / 2.0)
    return np.maximum(sigma, float(floor_arcsec))


def candidate_pairs_within_radius(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_ra: str = "ra",
    left_dec: str = "dec",
    right_ra: str = "ra",
    right_dec: str = "dec",
    radius_arcsec: float = 5.0,
) -> pd.DataFrame:
    """Return every finite-coordinate pair within ``radius_arcsec``.

    Positional row numbers are returned rather than dataframe labels so that
    downstream joins remain unambiguous even when inputs use custom indexes.
    """

    columns = ["left_index", "right_index", "distance_arcsec"]
    if not np.isfinite(radius_arcsec) or radius_arcsec <= 0:
        raise ValueError("radius_arcsec must be finite and positive")
    if left_df.empty or right_df.empty:
        return pd.DataFrame(columns=columns)

    left_ra_values = pd.to_numeric(left_df[left_ra], errors="coerce").to_numpy()
    left_dec_values = pd.to_numeric(left_df[left_dec], errors="coerce").to_numpy()
    right_ra_values = pd.to_numeric(right_df[right_ra], errors="coerce").to_numpy()
    right_dec_values = pd.to_numeric(right_df[right_dec], errors="coerce").to_numpy()

    left_valid = np.isfinite(left_ra_values) & np.isfinite(left_dec_values)
    right_valid = np.isfinite(right_ra_values) & np.isfinite(right_dec_values)
    if not left_valid.any() or not right_valid.any():
        return pd.DataFrame(columns=columns)

    left_positions = np.flatnonzero(left_valid)
    right_positions = np.flatnonzero(right_valid)
    left_coords = SkyCoord(
        ra=left_ra_values[left_valid] * u.deg,
        dec=left_dec_values[left_valid] * u.deg,
        frame="icrs",
    )
    right_coords = SkyCoord(
        ra=right_ra_values[right_valid] * u.deg,
        dec=right_dec_values[right_valid] * u.deg,
        frame="icrs",
    )

    left_idx, right_idx, separations, _ = search_around_sky(
        left_coords,
        right_coords,
        seplimit=float(radius_arcsec) * u.arcsec,
    )
    return pd.DataFrame(
        {
            "left_index": left_positions[left_idx],
            "right_index": right_positions[right_idx],
            "distance_arcsec": separations.arcsec,
        }
    ).sort_values(["left_index", "distance_arcsec"], ignore_index=True)


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
