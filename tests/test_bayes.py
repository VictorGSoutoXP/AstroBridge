import numpy as np
import pytest

from astrobridge.bayes import (
    ARCSEC_TO_RAD,
    budavari_szalay_bayes_factor,
    catalog_prior_odds,
    cone_solid_angle_sr,
    posterior_from_bayes_factor,
)


def test_bayes_factor_decreases_with_distance():
    close = budavari_szalay_bayes_factor(np.array([0.1]))[0]
    far = budavari_szalay_bayes_factor(np.array([2.0]))[0]
    assert close > far


def test_bayes_factor_converts_arcseconds_to_radians():
    variance_rad = (0.1**2 + 0.5**2) * ARCSEC_TO_RAD**2
    result = budavari_szalay_bayes_factor(np.array([0.0]), 0.1, 0.5)[0]
    assert result == pytest.approx(2.0 / variance_rad)


def test_posterior_between_zero_and_one():
    p = posterior_from_bayes_factor(np.array([1.0, 10.0, 100.0]))
    assert np.all(p > 0)
    assert np.all(p < 1)


def test_posterior_accepts_explicit_prior_odds():
    result = posterior_from_bayes_factor(np.array([10.0]), prior_odds=0.1)
    assert result[0] == pytest.approx(0.5)


def test_posterior_rejects_conflicting_priors():
    with pytest.raises(ValueError, match="not both"):
        posterior_from_bayes_factor(np.array([1.0]), prior_match_probability=0.5, prior_odds=0.1)


def test_posterior_rejects_nonfinite_prior_odds():
    with pytest.raises(ValueError, match="finite"):
        posterior_from_bayes_factor(np.array([1.0]), prior_odds=np.nan)


def test_catalog_prior_odds_matches_density_expression():
    area = cone_solid_angle_sr(0.3)
    odds = catalog_prior_odds(100, 80, area, expected_match_fraction=0.5)
    probability = 40 * area / (100 * 80)
    assert odds == pytest.approx(probability / (1 - probability))
