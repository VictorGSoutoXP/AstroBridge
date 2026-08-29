import json
import math

import pandas as pd
import pytest

from astrobridge.external_benchmark import (
    BenchmarkSchemaError,
    evaluate_external_benchmark,
    validate_external_benchmark,
)

CANDIDATE_COLUMNS = [
    "case_id",
    "left_id",
    "right_id",
    "posterior_match",
    "selected",
    "component_id",
]


def _cases(rows):
    return pd.DataFrame(
        rows,
        columns=["case_id", "left_id", "truth_state", "truth_complete"],
    )


def _truth(rows):
    return pd.DataFrame(rows, columns=["case_id", "right_id", "relation"])


def _candidates(rows):
    return pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)


def test_evaluator_separates_candidate_pair_and_decision_metrics():
    cases = _cases(
        [
            ("p1", "left-p1", "matched", True),
            ("p2", "left-p2", "matched", True),
            ("n1", "left-n1", "unmatched", True),
            ("a1", "left-a1", "ambiguous", False),
        ]
    )
    truth = _truth(
        [
            ("p1", "right-1", "unique_true"),
            ("p2", "right-2", "unique_true"),
            ("a1", "right-a", "acceptable"),
        ]
    )
    candidates = _candidates(
        [
            ("p1", "left-p1", "right-1", 0.9, True, "strict-1"),
            ("p1", "left-p1", "bridge", 0.1, False, "strict-1"),
            ("p2", "left-p2", "right-2", 0.4, False, "strict-1"),
            ("p2", "left-p2", "bridge", 0.6, False, "strict-1"),
            ("n1", "left-n1", "right-n", 0.8, True, "strict-2"),
            ("a1", "left-a1", "right-a", 0.7, True, "ambiguous-1"),
        ]
    )

    result = evaluate_external_benchmark(cases, truth, candidates)

    assert result.counts.strict_cases == 3
    assert result.counts.excluded_ambiguous_cases == 1
    assert result.candidate_generation.candidate_coverage.value == pytest.approx(1.0)
    assert result.candidate_generation.truth_candidate_rank_by_case == {"p1": 1, "p2": 2}
    assert result.candidate_generation.mean_truth_candidate_rank_when_present.value == 1.5
    assert result.pairwise_calibration.scored_pairs == 5
    assert result.pairwise_calibration.positive_pairs == 2
    assert result.pairwise_calibration.negative_pairs == 3
    assert result.pairwise_calibration.average_precision.value == pytest.approx(0.75)
    assert result.decision.true_positives == 1
    assert result.decision.false_positives == 1
    assert result.decision.false_negatives == 1
    assert result.decision.true_negatives == 0
    assert result.decision.precision.value == pytest.approx(0.5)
    assert result.decision.recall.value == pytest.approx(0.5)
    assert result.decision.f1.value == pytest.approx(0.5)
    assert result.decision.false_positive_rate_on_unmatched.value == pytest.approx(1.0)
    assert result.decision.exact_decision_accuracy.value == pytest.approx(1 / 3)
    assert result.decision.selection_rate.value == pytest.approx(2 / 3)
    assert result.decision.abstention_rate.value == pytest.approx(1 / 3)
    json.dumps(result.to_dict(), allow_nan=False)


def test_wrong_counterpart_counts_as_false_positive_and_false_negative():
    cases = _cases(
        [
            ("p", "left-p", "matched", True),
            ("n", "left-n", "unmatched", True),
        ]
    )
    truth = _truth([("p", "right-true", "unique_true")])
    candidates = _candidates(
        [
            ("p", "left-p", "right-wrong", 0.9, True, "p-component"),
        ]
    )

    result = evaluate_external_benchmark(cases, truth, candidates)

    assert result.decision.true_positives == 0
    assert result.decision.false_positives == 1
    assert result.decision.false_negatives == 1
    assert result.decision.true_negatives == 1
    assert result.decision.wrong_counterpart_selections == 1
    assert result.decision.selections_on_unmatched == 0
    assert result.decision.precision.value == 0.0
    assert result.decision.recall.value == 0.0
    assert result.decision.f1.value == 0.0
    assert result.decision.false_positive_rate_on_unmatched.value == 0.0


def test_missing_true_candidate_and_no_predictions_have_explicit_undefined_metrics():
    cases = _cases([("p", "left-p", "matched", True)])
    truth = _truth([("p", "right-true", "unique_true")])
    candidates = _candidates([])

    result = evaluate_external_benchmark(cases, truth, candidates)

    assert result.candidate_generation.candidate_coverage.value == 0.0
    assert result.candidate_generation.truth_candidate_rank_by_case == {"p": None}
    assert result.candidate_generation.mean_truth_candidate_rank_when_present.value is None
    assert (
        result.candidate_generation.mean_truth_candidate_rank_when_present.undefined_reason
        == "no_true_pairs_in_candidates"
    )
    assert result.pairwise_calibration.micro.brier_score.value is None
    assert (
        result.pairwise_calibration.micro.brier_score.undefined_reason
        == "no_strict_candidate_pairs"
    )
    assert result.decision.precision.value is None
    assert result.decision.precision.undefined_reason == "no_selected_pairs_in_strict_cases"
    assert result.decision.recall.value == 0.0
    assert result.decision.f1.value == 0.0
    assert result.decision.false_positive_rate_on_unmatched.value is None
    assert result.decision.abstention_rate.value == 1.0
    json.dumps(result.to_dict(), allow_nan=False)


def test_pairwise_calibration_micro_and_source_balanced_are_exact():
    cases = _cases(
        [
            ("p", "left-p", "matched", True),
            ("n", "left-n", "unmatched", True),
        ]
    )
    truth = _truth([("p", "right-true", "unique_true")])
    candidates = _candidates(
        [
            ("p", "left-p", "right-true", 0.8, True, "p-component"),
            ("p", "left-p", "right-false", 0.6, False, "p-component"),
            ("n", "left-n", "right-negative", 0.2, False, "n-component"),
        ]
    )

    result = evaluate_external_benchmark(cases, truth, candidates)
    calibration = result.pairwise_calibration

    assert calibration.micro.brier_score.value == pytest.approx((0.04 + 0.36 + 0.04) / 3)
    assert calibration.source_balanced.brier_score.value == pytest.approx(0.12)
    expected_micro_log_loss = (-math.log(0.8) - math.log(0.4) - math.log(0.8)) / 3
    assert calibration.micro.log_loss.value == pytest.approx(expected_micro_log_loss)
    assert calibration.micro.expected_calibration_error.value == pytest.approx(
        (0.2 + 0.6 + 0.2) / 3
    )
    assert calibration.average_precision.value == 1.0
    assert len(calibration.micro.bins) == 10
    assert calibration.micro.bins[2].pair_count == 1
    assert calibration.micro.bins[6].pair_count == 1
    assert calibration.micro.bins[8].pair_count == 1
    assert calibration.micro.bins[0].mean_probability.value is None
    assert calibration.micro.bins[0].mean_probability.undefined_reason == "no_pairs_in_bin"


def test_log_loss_clips_boundary_probabilities_and_remains_json_safe():
    cases = _cases(
        [
            ("p", "left-p", "matched", True),
            ("n", "left-n", "unmatched", True),
        ]
    )
    truth = _truth([("p", "right-true", "unique_true")])
    candidates = _candidates(
        [
            ("p", "left-p", "right-true", 1.0, True, "p-component"),
            ("n", "left-n", "right-negative", 0.0, False, "n-component"),
        ]
    )

    result = evaluate_external_benchmark(cases, truth, candidates)

    assert result.pairwise_calibration.micro.log_loss.value is not None
    assert math.isfinite(result.pairwise_calibration.micro.log_loss.value)
    assert result.pairwise_calibration.micro.expected_calibration_error.value == 0.0
    assert result.pairwise_calibration.micro.bins[9].pair_count == 1
    json.dumps(result.to_dict(), allow_nan=False)


def test_ambiguous_and_unknown_cases_are_excluded_when_components_are_separate():
    cases = _cases(
        [
            ("p", "left-p", "matched", True),
            ("a", "left-a", "ambiguous", False),
            ("u", "left-u", "unknown", False),
        ]
    )
    truth = _truth(
        [
            ("p", "right-p", "unique_true"),
            ("a", "right-a", "acceptable"),
        ]
    )
    candidates = _candidates(
        [
            ("p", "left-p", "right-p", 0.9, True, "strict"),
            ("a", "left-a", "right-a", 0.8, True, "ambiguous"),
            ("u", "left-u", "right-u", 0.7, True, "unknown"),
        ]
    )

    result = evaluate_external_benchmark(cases, truth, candidates)

    assert result.counts.total_cases == 3
    assert result.counts.strict_cases == 1
    assert result.counts.excluded_ambiguous_cases == 1
    assert result.counts.excluded_unknown_cases == 1
    assert result.decision.selected_pairs == 1
    assert result.decision.true_positives == 1


def test_component_mixing_strict_and_non_strict_truth_is_rejected():
    cases = _cases(
        [
            ("p", "left-p", "matched", True),
            ("a", "left-a", "ambiguous", False),
        ]
    )
    truth = _truth(
        [
            ("p", "right-p", "unique_true"),
            ("a", "shared", "acceptable"),
        ]
    )
    candidates = _candidates(
        [
            ("p", "left-p", "shared", 0.4, False, "mixed"),
            ("a", "left-a", "shared", 0.5, False, "mixed"),
        ]
    )

    with pytest.raises(BenchmarkSchemaError, match="mixes strict cases"):
        validate_external_benchmark(cases, truth, candidates)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.assign(case_id=[1]), "string identifiers"),
        (lambda frame: frame.assign(posterior_match=[1.1]), "probabilities in"),
        (lambda frame: frame.assign(selected=["yes"]), "must contain booleans"),
    ],
)
def test_invalid_candidate_schema_is_rejected(mutation, message):
    cases = _cases([("p", "left-p", "matched", True)])
    truth = _truth([("p", "right-p", "unique_true")])
    candidates = _candidates([("p", "left-p", "right-p", 0.9, True, "component")])

    with pytest.raises(BenchmarkSchemaError, match=message):
        validate_external_benchmark(cases, truth, mutation(candidates))


def test_selected_pairs_must_be_one_to_one():
    cases = _cases(
        [
            ("p1", "left-1", "matched", True),
            ("p2", "left-2", "matched", True),
        ]
    )
    truth = _truth(
        [
            ("p1", "truth-1", "unique_true"),
            ("p2", "truth-2", "unique_true"),
        ]
    )
    candidates = _candidates(
        [
            ("p1", "left-1", "shared", 0.9, True, "component"),
            ("p2", "left-2", "shared", 0.8, True, "component"),
        ]
    )

    with pytest.raises(BenchmarkSchemaError, match="unique on right_id"):
        validate_external_benchmark(cases, truth, candidates)


def test_disconnected_declared_component_is_rejected():
    cases = _cases(
        [
            ("p1", "left-1", "matched", True),
            ("p2", "left-2", "matched", True),
        ]
    )
    truth = _truth(
        [
            ("p1", "truth-1", "unique_true"),
            ("p2", "truth-2", "unique_true"),
        ]
    )
    candidates = _candidates(
        [
            ("p1", "left-1", "truth-1", 0.9, True, "bad-component"),
            ("p2", "left-2", "truth-2", 0.8, True, "bad-component"),
        ]
    )

    with pytest.raises(BenchmarkSchemaError, match="disconnected"):
        validate_external_benchmark(cases, truth, candidates)


def test_truth_schema_rules_are_strict():
    cases = _cases(
        [
            ("m", "left-m", "matched", True),
            ("u", "left-u", "unknown", False),
        ]
    )
    candidates = _candidates([])

    with pytest.raises(BenchmarkSchemaError, match="exactly one unique_true"):
        validate_external_benchmark(cases, _truth([]), candidates)
    with pytest.raises(BenchmarkSchemaError, match="unknown case"):
        validate_external_benchmark(
            cases,
            _truth(
                [
                    ("m", "right-m", "unique_true"),
                    ("u", "right-u", "acceptable"),
                ]
            ),
            candidates,
        )


def test_average_precision_is_tie_invariant():
    cases = _cases(
        [
            ("p1", "left-1", "matched", True),
            ("p2", "left-2", "matched", True),
            ("n", "left-n", "unmatched", True),
        ]
    )
    truth = _truth(
        [
            ("p1", "truth-1", "unique_true"),
            ("p2", "truth-2", "unique_true"),
        ]
    )
    rows = [
        ("p1", "left-1", "truth-1", 0.8, True, "one"),
        ("p1", "left-1", "false-1", 0.8, False, "one"),
        ("p2", "left-2", "truth-2", 0.4, True, "two"),
        ("n", "left-n", "false-n", 0.4, False, "three"),
    ]

    first = evaluate_external_benchmark(cases, truth, _candidates(rows))
    second = evaluate_external_benchmark(cases, truth, _candidates(list(reversed(rows))))

    assert first.pairwise_calibration.average_precision.value == pytest.approx(0.5)
    assert (
        second.pairwise_calibration.average_precision.value
        == first.pairwise_calibration.average_precision.value
    )
