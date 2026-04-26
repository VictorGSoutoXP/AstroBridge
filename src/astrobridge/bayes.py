from __future__ import annotations

import numpy as np
import pandas as pd


def budavari_szalay_bayes_factor(
    separation_arcsec: pd.Series | np.ndarray,
    sigma1_arcsec: float | pd.Series | np.ndarray = 0.1,
    sigma2_arcsec: float | pd.Series | np.ndarray = 0.5,
) -> np.ndarray:
    sep = np.asarray(separation_arcsec, dtype=float)
    s1 = np.asarray(sigma1_arcsec, dtype=float)
    s2 = np.asarray(sigma2_arcsec, dtype=float)

    variance = s1**2 + s2**2
    variance = np.where(variance <= 0, np.nan, variance)

    return (2.0 / variance) * np.exp(-(sep**2) / (2.0 * variance))


def posterior_from_bayes_factor(
    bayes_factor: pd.Series | np.ndarray,
    prior_match_probability: float = 0.5,
) -> np.ndarray:
    b = np.asarray(bayes_factor, dtype=float)
    p = float(prior_match_probability)

    odds = p / (1.0 - p)
    posterior_odds = b * odds

    return posterior_odds / (1.0 + posterior_odds)
