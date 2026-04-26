import numpy as np

from astrobridge.bayes import budavari_szalay_bayes_factor, posterior_from_bayes_factor


def test_bayes_factor_decreases_with_distance():
    close = budavari_szalay_bayes_factor(np.array([0.1]))[0]
    far = budavari_szalay_bayes_factor(np.array([2.0]))[0]
    assert close > far


def test_posterior_between_zero_and_one():
    p = posterior_from_bayes_factor(np.array([1.0, 10.0, 100.0]))
    assert np.all(p > 0)
    assert np.all(p < 1)
