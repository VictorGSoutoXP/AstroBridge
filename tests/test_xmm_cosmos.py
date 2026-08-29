import numpy as np
import pandas as pd
import pytest

from astrobridge.xmm_cosmos import (
    XmmCosmosBenchmarkError,
    apply_component_closure,
    apply_logit_intercept,
    assign_bipartite_components,
    build_reference_bundle,
    cluster_bootstrap_ratios,
    component_split,
    fit_logit_intercept,
    wilson_interval,
)


def test_reference_bundle_separates_secure_ambiguous_and_unknown_cases():
    xmm = pd.DataFrame(
        {
            "ID": [1, 2, 3, 4, 5],
            "RA": [10.0, 11.0, 12.0, 13.0, 14.0],
            "DEC": [0.0] * 5,
            "pos_err": [1.0] * 5,
        }
    )
    irac = pd.DataFrame(
        {
            "ID": [101, 102, 103, 104],
            "RA": [10.0, 11.0, 11.0001, 12.0],
            "DEC": [0.0] * 4,
        }
    )
    chandra = pd.DataFrame(
        {
            "id_xmm": [1, 2, 2, 3, 4],
            "final_id_flag": [1, 1, 1, 10, -99],
            "ra_irac": [10.0, 11.0, 11.0001, 12.0, -99.0],
            "dec_irac": [0.0, 0.0, 0.0, 0.0, -99.0],
        }
    )

    bundle = build_reference_bundle(xmm, irac, chandra)
    states = bundle.cases.set_index("case_id")["truth_state"].to_dict()

    assert states == {
        "1": "matched",
        "2": "ambiguous",
        "3": "ambiguous",
        "4": "unknown",
        "5": "unknown",
    }
    assert bundle.cases.set_index("case_id").loc["1", "truth_complete"]
    assert set(map(tuple, bundle.truth_pairs.to_numpy())) == {
        ("1", "101", "unique_true"),
        ("2", "102", "acceptable"),
        ("2", "103", "acceptable"),
        ("3", "104", "acceptable"),
    }
    assert bundle.label_links["label_distance_arcsec"].max() < 0.5


def test_reference_bundle_rejects_reused_strict_counterpart():
    xmm = pd.DataFrame({"ID": [1, 2], "RA": [10.0, 10.0], "DEC": [0.0, 0.0], "pos_err": [1.0, 1.0]})
    irac = pd.DataFrame({"ID": [101], "RA": [10.0], "DEC": [0.0]})
    chandra = pd.DataFrame(
        {
            "id_xmm": [1, 2],
            "final_id_flag": [1, 1],
            "ra_irac": [10.0, 10.0],
            "dec_irac": [0.0, 0.0],
        }
    )

    with pytest.raises(XmmCosmosBenchmarkError, match="reuse IRAC IDs"):
        build_reference_bundle(xmm, irac, chandra)


def test_component_assignment_is_connected_and_row_order_invariant():
    candidates = pd.DataFrame(
        {
            "case_id": ["a", "b", "c"],
            "right_id": ["shared", "shared", "solo"],
        }
    )

    first = assign_bipartite_components(candidates)
    reversed_frame = candidates.iloc[::-1].reset_index(drop=True)
    second = assign_bipartite_components(reversed_frame)

    assert first.iloc[0] == first.iloc[1]
    assert first.iloc[2] != first.iloc[0]
    first_map = dict(zip(map(tuple, candidates.to_numpy()), first, strict=True))
    second_map = dict(zip(map(tuple, reversed_frame.to_numpy()), second, strict=True))
    assert first_map == second_map


def test_component_closure_excludes_mixed_truth_and_splits_closed_components():
    cases = pd.DataFrame(
        [
            ("a", "a", "matched", True, True),
            ("b", "b", "matched", True, True),
            ("c", "c", "ambiguous", False, False),
            ("d", "d", "matched", True, True),
        ],
        columns=[
            "case_id",
            "left_id",
            "truth_state",
            "truth_complete",
            "reference_truth_complete",
        ],
    )
    candidates = pd.DataFrame(
        {
            "case_id": ["a", "b", "c"],
            "right_id": ["right-a", "shared", "shared"],
        }
    )

    closed_cases, closed_candidates = apply_component_closure(cases, candidates)
    indexed = closed_cases.set_index("case_id")

    assert indexed.loc["a", "split"] in {"calibration", "test"}
    assert indexed.loc["a", "truth_complete"]
    assert indexed.loc["b", "split"] == "excluded"
    assert indexed.loc["b", "closure_excluded"]
    assert not indexed.loc["b", "truth_complete"]
    assert indexed.loc["c", "split"] == "excluded"
    assert indexed.loc["d", "split"] in {"calibration", "test"}
    assert indexed.loc["d", "component_id"]
    assert closed_candidates.loc[closed_candidates["case_id"].eq("b"), "split"].item() == (
        "excluded"
    )


def test_component_split_is_deterministic_and_order_independent():
    assert component_split(["2", "1"]) == component_split(["1", "2"])
    assert component_split(["1"]) in {"calibration", "test"}


def test_intercept_calibration_matches_observed_pair_prevalence():
    probabilities = np.full(4, 0.2)
    labels = np.array([1.0, 0.0, 0.0, 0.0])

    intercept = fit_logit_intercept(probabilities, labels)
    calibrated = apply_logit_intercept(probabilities, intercept)

    assert calibrated.mean() == pytest.approx(labels.mean(), abs=1e-12)
    assert calibrated == pytest.approx(np.full(4, 0.25), abs=1e-12)


def test_intercept_calibration_requires_both_classes():
    with pytest.raises(XmmCosmosBenchmarkError, match="positive and negative"):
        fit_logit_intercept([0.2, 0.3], [1, 1])


def test_wilson_interval_and_cluster_bootstrap_are_bounded_and_deterministic():
    lower, upper = wilson_interval(5, 10)
    assert lower == pytest.approx(0.236593, abs=1e-6)
    assert upper == pytest.approx(0.763407, abs=1e-6)
    counts = pd.DataFrame(
        {
            "success": [1, 0, 1],
            "total": [1, 1, 1],
            "selected": [1, 0, 1],
        }
    )
    ratios = {"coverage": ("success", "total"), "selection": ("selected", "total")}

    first = cluster_bootstrap_ratios(counts, ratios, replicates=200, seed=7)
    second = cluster_bootstrap_ratios(counts, ratios, replicates=200, seed=7)

    assert first == second
    assert 0.0 <= first["coverage"]["lower_95"] <= first["coverage"]["upper_95"] <= 1.0
