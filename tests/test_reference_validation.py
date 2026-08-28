import pandas as pd
import pytest

from astrobridge.matching import CrossmatchResult
from astrobridge.reference_cli import dataframe_sha256, identifier_sha256
from astrobridge.reference_validation import (
    clean_gaia_allwise_reference,
    evaluate_gaia_allwise_reference,
    gaia_allwise_reference_comparison,
)


def reference_table():
    return pd.DataFrame(
        {
            "source_id": [1, 2, 3, 4],
            "original_ext_source_id": ["A", "B", "C", "D"],
            "angular_distance": [0.1, 0.2, 0.3, 0.4],
            "xm_flag": [8, 8, 12, 8],
            "allwise_oid": [10, 11, 12, 13],
            "number_of_neighbours": [1, 1, 1, 2],
            "number_of_mates": [0, 0, 0, 0],
        }
    )


def test_clean_reference_removes_ambiguous_and_flagged_rows():
    clean = clean_gaia_allwise_reference(reference_table())
    assert list(clean["source_id"]) == [1, 2]


def test_identifier_manifest_hash_is_order_independent():
    assert identifier_sha256([3, 1, 2]) == identifier_sha256(["2", "3", "1"])


def test_dataframe_manifest_hash_is_order_independent():
    first = pd.DataFrame({"b": [2, 1], "a": ["y", "x"]})
    reordered = first.iloc[::-1][["a", "b"]].reset_index(drop=True)
    assert dataframe_sha256(first) == dataframe_sha256(reordered)


def test_reference_metrics_separate_candidate_coverage_and_selection():
    gaia = pd.DataFrame({"source_id": [1, 2, 3]})
    allwise = pd.DataFrame({"designation": ["A", "B", "C"]})
    candidates = pd.DataFrame(
        {
            "left_index": [0, 1],
            "right_index": [0, 2],
            "distance_arcsec": [0.1, 0.3],
            "posterior_match": [0.9, 0.8],
        }
    )
    matches = pd.DataFrame(
        {
            "gaia_source_id": [1, 2, 3],
            "wise_designation": ["A", "C", "C"],
            "distance_arcsec": [0.1, 0.3, 0.2],
            "posterior_match": [0.9, 0.8, 0.7],
        }
    )
    result = CrossmatchResult(matches=matches, candidates=candidates, prior_odds=1e-6)

    metrics = evaluate_gaia_allwise_reference(result, gaia, allwise, reference_table())

    assert metrics.clean_official_associations == 2
    assert metrics.reference_in_candidate_set == 1
    assert metrics.reference_missing_from_candidates == 1
    assert metrics.agreements == 1
    assert metrics.disagreements == 1
    assert metrics.reference_candidate_not_selected == 0
    assert metrics.selected_without_clean_reference == 1
    assert metrics.candidate_coverage == pytest.approx(0.5)
    assert metrics.agreement_rate_on_clean_reference == pytest.approx(0.5)
    assert metrics.agreement_when_selected == pytest.approx(0.5)
    assert metrics.selection_given_reference_candidate == pytest.approx(1.0)

    comparison = gaia_allwise_reference_comparison(result, gaia, allwise, reference_table())
    assert dict(zip(comparison["source_id"], comparison["status"], strict=True)) == {
        1: "agreement",
        2: "disagreement_reference_missing_from_candidates",
    }
    row = comparison.loc[comparison["source_id"] == 1].iloc[0]
    assert bool(row["candidate_present"])
    assert row["candidate_posterior"] == pytest.approx(0.9)


def test_reference_metrics_count_present_candidate_not_selected_separately():
    gaia = pd.DataFrame({"source_id": [1, 2]})
    allwise = pd.DataFrame({"designation": ["A", "B"]})
    candidates = pd.DataFrame(
        {
            "left_index": [0, 1],
            "right_index": [0, 1],
            "distance_arcsec": [0.1, 0.2],
            "posterior_match": [0.9, 0.2],
        }
    )
    matches = pd.DataFrame(
        {
            "gaia_source_id": [1],
            "wise_designation": ["A"],
            "distance_arcsec": [0.1],
            "posterior_match": [0.9],
        }
    )
    result = CrossmatchResult(matches=matches, candidates=candidates, prior_odds=1e-6)

    metrics = evaluate_gaia_allwise_reference(result, gaia, allwise, reference_table())

    assert metrics.reference_missing_from_candidates == 0
    assert metrics.reference_candidate_not_selected == 1


def test_reference_metrics_use_none_for_undefined_rates():
    gaia = pd.DataFrame({"source_id": [99]})
    allwise = pd.DataFrame({"designation": ["Z"]})
    empty = pd.DataFrame()
    result = CrossmatchResult(matches=empty, candidates=empty, prior_odds=0.0)
    no_clean_reference = reference_table().assign(xm_flag=1)

    metrics = evaluate_gaia_allwise_reference(result, gaia, allwise, no_clean_reference)

    assert metrics.candidate_coverage is None
    assert metrics.agreement_rate_on_clean_reference is None
    assert metrics.agreement_when_selected is None
    assert metrics.selection_given_reference_candidate is None
