from __future__ import annotations

import numpy as np
import pandas as pd

ARCSEC_TO_RAD = np.deg2rad(1.0 / 3600.0)


def budavari_szalay_bayes_factor(
    separation_arcsec: pd.Series | np.ndarray,
    sigma1_arcsec: float | pd.Series | np.ndarray = 0.1,
    sigma2_arcsec: float | pd.Series | np.ndarray = 0.5,
) -> np.ndarray:
    """Return the two-catalog Budavári-Szalay positional Bayes factor.

    Inputs are accepted in arcseconds and converted to radians before applying
    equation 16 of Budavári & Szalay (2008). Radians are dimensionless in the
    numerical expression, so the returned Bayes factor is dimensionless.
    """

    sep = np.asarray(separation_arcsec, dtype=float) * ARCSEC_TO_RAD
    s1 = np.asarray(sigma1_arcsec, dtype=float) * ARCSEC_TO_RAD
    s2 = np.asarray(sigma2_arcsec, dtype=float) * ARCSEC_TO_RAD

    if np.any(~np.isfinite(sep)) or np.any(sep < 0):
        raise ValueError("separations must be finite and non-negative")
    if np.any(~np.isfinite(s1)) or np.any(~np.isfinite(s2)):
        raise ValueError("positional uncertainties must be finite and positive")
    if np.any(s1 <= 0) or np.any(s2 <= 0):
        raise ValueError("positional uncertainties must be finite and positive")

    variance = s1**2 + s2**2
    return (2.0 / variance) * np.exp(-(sep**2) / (2.0 * variance))


def posterior_from_bayes_factor(
    bayes_factor: pd.Series | np.ndarray,
    prior_match_probability: float | None = None,
    *,
    prior_odds: float | pd.Series | np.ndarray | None = None,
) -> np.ndarray:
    """Convert Bayes factors to posterior probabilities with explicit priors."""

    b = np.asarray(bayes_factor, dtype=float)
    if np.any(np.isnan(b)) or np.any(b < 0):
        raise ValueError("bayes_factor must be non-negative and not NaN")
    if prior_match_probability is not None and prior_odds is not None:
        raise ValueError("provide prior_match_probability or prior_odds, not both")

    if prior_odds is None:
        p = 0.5 if prior_match_probability is None else float(prior_match_probability)
        if not 0.0 < p < 1.0:
            raise ValueError("prior_match_probability must be between zero and one")
        odds = np.asarray(p / (1.0 - p), dtype=float)
    else:
        odds = np.asarray(prior_odds, dtype=float)
        if np.any(~np.isfinite(odds)) or np.any(odds < 0):
            raise ValueError("prior_odds must be finite and non-negative")

    posterior_odds = b * odds
    with np.errstate(over="ignore", invalid="ignore"):
        posterior = posterior_odds / (1.0 + posterior_odds)
    return np.where(np.isposinf(posterior_odds), 1.0, posterior)


def cone_solid_angle_sr(radius_deg: float) -> float:
    """Return the exact solid angle of a spherical cone in steradians."""

    if not 0.0 < radius_deg <= 180.0:
        raise ValueError("radius_deg must be in the interval (0, 180]")
    return float(2.0 * np.pi * (1.0 - np.cos(np.deg2rad(radius_deg))))


def catalog_prior_odds(
    n_left: int,
    n_right: int,
    area_solid_angle_sr: float,
    expected_match_fraction: float = 0.7,
) -> float:
    """Estimate association prior odds from catalog density and expected matches.

    The density prior probability is ``N_match * area / (N_left * N_right)``,
    following the finite-footprint treatment in Budavári & Szalay (2008). It is
    converted to odds exactly. Scientific analyses should report a sensitivity
    study over ``expected_match_fraction``.
    """

    if n_left <= 0 or n_right <= 0:
        raise ValueError("catalog sizes must be positive")
    if not 0 < area_solid_angle_sr <= 4.0 * np.pi:
        raise ValueError("area_solid_angle_sr must be in the interval (0, 4*pi]")
    if not 0.0 <= expected_match_fraction <= 1.0:
        raise ValueError("expected_match_fraction must be between zero and one")

    expected_matches = expected_match_fraction * min(n_left, n_right)
    prior_probability = expected_matches * area_solid_angle_sr / (n_left * n_right)
    if prior_probability >= 1.0:
        raise ValueError("density prior must be below one; revise the catalog footprint")
    return float(prior_probability / (1.0 - prior_probability))
