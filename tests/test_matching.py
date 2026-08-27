import pandas as pd

from astrobridge.matching import probabilistic_crossmatch, resolve_unique_matches


def test_unique_resolution_uses_alternative_candidate_for_global_solution():
    candidates = pd.DataFrame(
        {
            "left_index": [0, 0, 1, 1],
            "right_index": [0, 1, 0, 1],
            "posterior_match": [0.90, 0.80, 0.85, 0.10],
        }
    )

    selected = resolve_unique_matches(candidates, min_score=0.05)

    assert set(zip(selected["left_index"], selected["right_index"], strict=True)) == {
        (0, 1),
        (1, 0),
    }


def test_unique_resolution_can_leave_source_unmatched():
    candidates = pd.DataFrame({"left_index": [0], "right_index": [0], "posterior_match": [0.49]})
    assert resolve_unique_matches(candidates, min_score=0.5).empty


def test_probabilistic_crossmatch_scores_all_nearby_pairs_and_is_unique():
    left = pd.DataFrame({"source_id": [1, 2], "ra_epoch": [10.0, 10.0001], "dec": [0, 0]})
    right = pd.DataFrame({"designation": ["a", "b"], "ra": [10.00005, 10.0002], "dec": [0, 0]})

    result = probabilistic_crossmatch(
        left,
        right,
        left_sigma_arcsec=0.1,
        right_sigma_arcsec=0.5,
        left_ra="ra_epoch",
        candidate_radius_arcsec=1.0,
        min_posterior=0.5,
        prior_odds=1e-10,
    )

    assert len(result.candidates) == 4
    assert len(result.matches) == 2
    assert result.matches["gaia_source_id"].is_unique
    assert result.matches["wise_designation"].is_unique


def test_probabilistic_crossmatch_handles_empty_catalog():
    empty = pd.DataFrame(columns=["ra", "dec"])
    right = pd.DataFrame({"ra": [10.0], "dec": [0.0]})

    result = probabilistic_crossmatch(
        empty,
        right,
        left_sigma_arcsec=0.1,
        right_sigma_arcsec=0.5,
    )

    assert result.matches.empty
    assert result.candidates.empty
    assert result.prior_odds == 0.0
