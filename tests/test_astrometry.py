import numpy as np
import pandas as pd
import pytest

from astrobridge.astrometry import (
    candidate_pairs_within_radius,
    effective_circular_sigma_arcsec,
    propagate_gaia_position,
)


def test_propagate_gaia_position_and_uncertainty():
    gaia = pd.DataFrame(
        {
            "ra": [10.0],
            "dec": [60.0],
            "pmra": [1000.0],
            "pmdec": [-500.0],
            "ra_error": [10.0],
            "dec_error": [20.0],
            "pmra_error": [2.0],
            "pmdec_error": [4.0],
        }
    )

    propagated = propagate_gaia_position(gaia, from_epoch=2016.0, to_epoch=2015.0)

    assert propagated.loc[0, "ra_epoch"] == pytest.approx(10.0 - 1000 / 3.6e6 / 0.5)
    assert propagated.loc[0, "dec_epoch"] == pytest.approx(60.0 + 500 / 3.6e6)
    ra_sigma = np.hypot(10.0, 2.0) / 1000.0
    dec_sigma = np.hypot(20.0, 4.0) / 1000.0
    assert propagated.loc[0, "position_sigma_arcsec"] == pytest.approx(
        np.sqrt((ra_sigma**2 + dec_sigma**2) / 2.0)
    )
    assert bool(propagated.loc[0, "proper_motion_available"])


def test_candidate_pairs_returns_every_pair_within_radius():
    left = pd.DataFrame({"ra": [10.0, 10.0001], "dec": [0.0, 0.0]})
    right = pd.DataFrame({"ra": [10.00005, 10.0002], "dec": [0.0, 0.0]})

    candidates = candidate_pairs_within_radius(left, right, radius_arcsec=1.0)

    assert set(zip(candidates["left_index"], candidates["right_index"], strict=True)) == {
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    }


def test_effective_circular_sigma_uses_default_for_invalid_values():
    result = effective_circular_sigma_arcsec(
        np.array([0.1, np.nan]), np.array([0.3, -1.0]), default_arcsec=0.5
    )
    assert result[0] == pytest.approx(np.sqrt((0.1**2 + 0.3**2) / 2.0))
    assert result[1] == pytest.approx(0.5)
