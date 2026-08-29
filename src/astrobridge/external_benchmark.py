from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

CASE_COLUMNS = {
    "case_id",
    "left_id",
    "truth_state",
    "truth_complete",
}
TRUTH_PAIR_COLUMNS = {"case_id", "right_id", "relation"}
PREDICTED_CANDIDATE_COLUMNS = {
    "case_id",
    "left_id",
    "right_id",
    "posterior_match",
    "selected",
    "component_id",
}

TRUTH_STATES = {"matched", "unmatched", "ambiguous", "unknown"}
TRUTH_RELATIONS = {"unique_true", "acceptable"}
ECE_BIN_COUNT = 10
LOG_LOSS_EPSILON = 1e-12


class BenchmarkSchemaError(ValueError):
    """Raised when benchmark truth or predictions are not safely evaluable."""


@dataclass(frozen=True)
class MetricValue:
    """A metric value with an explicit reason whenever it is undefined."""

    value: float | None
    undefined_reason: str | None = None

    def __post_init__(self) -> None:
        if self.value is None and self.undefined_reason is None:
            raise ValueError("an undefined metric must include undefined_reason")
        if self.value is not None and self.undefined_reason is not None:
            raise ValueError("a defined metric cannot include undefined_reason")
        if self.value is not None and not np.isfinite(self.value):
            raise ValueError("metric values must be finite")


@dataclass(frozen=True)
class DatasetCounts:
    total_cases: int
    strict_cases: int
    strict_matched_cases: int
    strict_unmatched_cases: int
    excluded_ambiguous_cases: int
    excluded_unknown_cases: int
    excluded_incomplete_cases: int
    candidate_pairs: int
    selected_pairs: int


@dataclass(frozen=True)
class CandidateGenerationMetrics:
    strict_matched_cases: int
    truth_in_candidates: int
    truth_missing_from_candidates: int
    candidate_coverage: MetricValue
    truth_candidate_rank_by_case: dict[str, int | None]
    mean_truth_candidate_rank_when_present: MetricValue
    median_truth_candidate_rank_when_present: MetricValue


@dataclass(frozen=True)
class CalibrationBin:
    bin_index: int
    lower_bound: float
    upper_bound: float
    includes_upper_bound: bool
    pair_count: int
    weight_sum: float
    mean_probability: MetricValue
    observed_positive_rate: MetricValue
    absolute_calibration_gap: MetricValue


@dataclass(frozen=True)
class CalibrationView:
    weighting: str
    brier_score: MetricValue
    log_loss: MetricValue
    expected_calibration_error: MetricValue
    bins: list[CalibrationBin]


@dataclass(frozen=True)
class PairwiseCalibrationMetrics:
    scope: str
    scored_pairs: int
    positive_pairs: int
    negative_pairs: int
    sources_with_scored_pairs: int
    log_loss_epsilon: float
    average_precision: MetricValue
    micro: CalibrationView
    source_balanced: CalibrationView


@dataclass(frozen=True)
class DecisionMetrics:
    strict_cases: int
    strict_matched_cases: int
    strict_unmatched_cases: int
    selected_pairs: int
    abstentions: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    wrong_counterpart_selections: int
    selections_on_unmatched: int
    positive_abstentions: int
    precision: MetricValue
    recall: MetricValue
    f1: MetricValue
    false_positive_rate_on_unmatched: MetricValue
    exact_decision_accuracy: MetricValue
    selection_rate: MetricValue
    abstention_rate: MetricValue
    positive_abstention_rate: MetricValue
    negative_abstention_rate: MetricValue


@dataclass(frozen=True)
class ExternalBenchmarkEvaluation:
    """JSON-serializable evaluation of a complete external benchmark bundle."""

    counts: DatasetCounts
    candidate_generation: CandidateGenerationMetrics
    pairwise_calibration: PairwiseCalibrationMetrics
    decision: DecisionMetrics

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _defined(value: float) -> MetricValue:
    return MetricValue(float(value))


def _undefined(reason: str) -> MetricValue:
    return MetricValue(None, reason)


def _ratio(numerator: int, denominator: int, reason: str) -> MetricValue:
    if denominator == 0:
        return _undefined(reason)
    return _defined(numerator / denominator)


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise BenchmarkSchemaError(f"{name} missing columns: {sorted(missing)}")


def _require_string_ids(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    for column in columns:
        invalid = frame[column].map(lambda value: not isinstance(value, str) or not value.strip())
        if invalid.any():
            raise BenchmarkSchemaError(f"{name}.{column} must contain non-empty string identifiers")


def _require_booleans(frame: pd.DataFrame, column: str, name: str) -> None:
    invalid = frame[column].map(lambda value: not isinstance(value, (bool, np.bool_)))
    if invalid.any():
        raise BenchmarkSchemaError(f"{name}.{column} must contain booleans")


def _validate_component_connectivity(candidates: pd.DataFrame) -> None:
    """Require each declared component to be one connected bipartite graph."""

    for component_id, component in candidates.groupby("component_id", sort=False):
        adjacency: dict[tuple[str, str], set[tuple[str, str]]] = {}
        for row in component.itertuples(index=False):
            left_node = ("left", str(row.case_id))
            right_node = ("right", str(row.right_id))
            adjacency.setdefault(left_node, set()).add(right_node)
            adjacency.setdefault(right_node, set()).add(left_node)

        seed = next(iter(adjacency))
        visited = {seed}
        queue = [seed]
        while queue:
            node = queue.pop()
            for neighbour in adjacency[node]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)
        if len(visited) != len(adjacency):
            raise BenchmarkSchemaError(
                f"component_id {component_id!r} contains disconnected candidate graphs"
            )


def validate_external_benchmark(
    cases: pd.DataFrame,
    truth_pairs: pd.DataFrame,
    predicted_candidates: pd.DataFrame,
) -> None:
    """Validate a benchmark bundle, rejecting incomplete one-to-one components.

    Strict metrics use only complete ``matched`` and ``unmatched`` cases. A
    component containing any strict case must contain only strict cases because
    assignment decisions are coupled across the entire component.
    """

    _require_columns(cases, CASE_COLUMNS, "cases")
    _require_columns(truth_pairs, TRUTH_PAIR_COLUMNS, "truth_pairs")
    _require_columns(
        predicted_candidates,
        PREDICTED_CANDIDATE_COLUMNS,
        "predicted_candidates",
    )
    _require_string_ids(cases, ("case_id", "left_id"), "cases")
    _require_string_ids(truth_pairs, ("case_id", "right_id"), "truth_pairs")
    _require_string_ids(
        predicted_candidates,
        ("case_id", "left_id", "right_id", "component_id"),
        "predicted_candidates",
    )
    _require_booleans(cases, "truth_complete", "cases")
    _require_booleans(predicted_candidates, "selected", "predicted_candidates")

    if cases["case_id"].duplicated().any():
        raise BenchmarkSchemaError("cases.case_id must be unique")
    if cases["left_id"].duplicated().any():
        raise BenchmarkSchemaError("cases.left_id must be unique")
    if truth_pairs.duplicated(["case_id", "right_id"]).any():
        raise BenchmarkSchemaError("truth_pairs must contain unique case_id/right_id pairs")
    if predicted_candidates.duplicated(["case_id", "right_id"]).any():
        raise BenchmarkSchemaError(
            "predicted_candidates must contain unique case_id/right_id pairs"
        )

    invalid_states = set(cases["truth_state"]).difference(TRUTH_STATES)
    if invalid_states:
        raise BenchmarkSchemaError(f"invalid truth_state values: {sorted(invalid_states)}")
    invalid_relations = set(truth_pairs["relation"]).difference(TRUTH_RELATIONS)
    if invalid_relations:
        raise BenchmarkSchemaError(f"invalid truth relation values: {sorted(invalid_relations)}")

    case_ids = set(cases["case_id"])
    unknown_truth_cases = set(truth_pairs["case_id"]).difference(case_ids)
    unknown_candidate_cases = set(predicted_candidates["case_id"]).difference(case_ids)
    if unknown_truth_cases:
        raise BenchmarkSchemaError(
            f"truth_pairs references unknown cases: {sorted(unknown_truth_cases)}"
        )
    if unknown_candidate_cases:
        raise BenchmarkSchemaError(
            f"predicted_candidates references unknown cases: {sorted(unknown_candidate_cases)}"
        )

    case_to_left = dict(zip(cases["case_id"], cases["left_id"], strict=True))
    expected_left = predicted_candidates["case_id"].map(case_to_left)
    wrong_left = predicted_candidates.loc[expected_left.ne(predicted_candidates["left_id"])]
    if not wrong_left.empty:
        raise BenchmarkSchemaError("candidate left_id does not match its case_id")

    probabilities = pd.to_numeric(
        predicted_candidates["posterior_match"], errors="coerce"
    ).to_numpy(dtype=float)
    if np.any(~np.isfinite(probabilities)) or np.any((probabilities < 0.0) | (probabilities > 1.0)):
        raise BenchmarkSchemaError(
            "predicted_candidates.posterior_match must contain finite probabilities in [0, 1]"
        )

    truth_by_case = {
        case_id: group for case_id, group in truth_pairs.groupby("case_id", sort=False)
    }
    empty_truth = truth_pairs.iloc[0:0]
    for case in cases.itertuples(index=False):
        case_truth = truth_by_case.get(case.case_id, empty_truth)
        relations = case_truth["relation"].tolist()
        if case.truth_state == "matched":
            if relations.count("unique_true") != 1 or len(relations) != 1:
                raise BenchmarkSchemaError(
                    f"matched case {case.case_id!r} must have exactly one unique_true pair"
                )
        elif case.truth_state == "unmatched" and relations:
            raise BenchmarkSchemaError(f"unmatched case {case.case_id!r} cannot have truth pairs")
        elif case.truth_state == "ambiguous" and any(
            relation != "acceptable" for relation in relations
        ):
            raise BenchmarkSchemaError(
                f"ambiguous case {case.case_id!r} may contain only acceptable pairs"
            )
        elif case.truth_state == "unknown" and relations:
            raise BenchmarkSchemaError(f"unknown case {case.case_id!r} cannot have truth pairs")
        if case.truth_state in {"ambiguous", "unknown"} and bool(case.truth_complete):
            raise BenchmarkSchemaError(
                f"{case.truth_state} case {case.case_id!r} cannot be truth_complete"
            )

    strict_mask = cases["truth_complete"] & cases["truth_state"].isin(["matched", "unmatched"])
    strict_case_ids = set(cases.loc[strict_mask, "case_id"])
    strict_matched_ids = set(cases.loc[strict_mask & cases["truth_state"].eq("matched"), "case_id"])
    strict_truth = truth_pairs.loc[
        truth_pairs["case_id"].isin(strict_matched_ids) & truth_pairs["relation"].eq("unique_true")
    ]
    if strict_truth["right_id"].duplicated().any():
        raise BenchmarkSchemaError("strict unique truth must be one-to-one on right_id")

    case_component_counts = predicted_candidates.groupby("case_id")["component_id"].nunique()
    if (case_component_counts > 1).any():
        raise BenchmarkSchemaError("a case_id cannot occur in multiple components")
    right_component_counts = predicted_candidates.groupby("right_id")["component_id"].nunique()
    if (right_component_counts > 1).any():
        raise BenchmarkSchemaError("a right_id cannot occur in multiple components")
    _validate_component_connectivity(predicted_candidates)

    for component_id, component in predicted_candidates.groupby("component_id", sort=False):
        component_cases = set(component["case_id"])
        if component_cases.intersection(strict_case_ids) and not component_cases.issubset(
            strict_case_ids
        ):
            raise BenchmarkSchemaError(
                f"component_id {component_id!r} mixes strict cases with incomplete, "
                "ambiguous, or unknown truth"
            )

    selected = predicted_candidates.loc[predicted_candidates["selected"]]
    if selected["left_id"].duplicated().any():
        raise BenchmarkSchemaError("selected candidates must be unique on left_id")
    if selected["right_id"].duplicated().any():
        raise BenchmarkSchemaError("selected candidates must be unique on right_id")


def _strict_cases(cases: pd.DataFrame) -> pd.DataFrame:
    return cases.loc[
        cases["truth_complete"] & cases["truth_state"].isin(["matched", "unmatched"])
    ].copy()


def _strict_truth_map(strict_cases: pd.DataFrame, truth_pairs: pd.DataFrame) -> dict[str, str]:
    matched_ids = set(strict_cases.loc[strict_cases["truth_state"].eq("matched"), "case_id"])
    strict_truth = truth_pairs.loc[
        truth_pairs["case_id"].isin(matched_ids) & truth_pairs["relation"].eq("unique_true")
    ]
    return dict(zip(strict_truth["case_id"], strict_truth["right_id"], strict=True))


def _candidate_generation_metrics(
    strict_cases: pd.DataFrame,
    truth_map: dict[str, str],
    candidates: pd.DataFrame,
) -> CandidateGenerationMetrics:
    candidates_by_case = {
        case_id: group for case_id, group in candidates.groupby("case_id", sort=False)
    }
    ranks: dict[str, int | None] = {}
    for case_id, true_right_id in truth_map.items():
        case_candidates = candidates_by_case.get(case_id)
        if case_candidates is None:
            ranks[case_id] = None
            continue
        true_rows = case_candidates.loc[case_candidates["right_id"].eq(true_right_id)]
        if true_rows.empty:
            ranks[case_id] = None
            continue
        true_probability = float(true_rows.iloc[0]["posterior_match"])
        ranks[case_id] = 1 + int(
            (pd.to_numeric(case_candidates["posterior_match"]) > true_probability).sum()
        )

    present_ranks = [rank for rank in ranks.values() if rank is not None]
    matched_count = int(strict_cases["truth_state"].eq("matched").sum())
    present_count = len(present_ranks)
    return CandidateGenerationMetrics(
        strict_matched_cases=matched_count,
        truth_in_candidates=present_count,
        truth_missing_from_candidates=matched_count - present_count,
        candidate_coverage=_ratio(
            present_count,
            matched_count,
            "no_strict_matched_cases",
        ),
        truth_candidate_rank_by_case=ranks,
        mean_truth_candidate_rank_when_present=(
            _defined(float(np.mean(present_ranks)))
            if present_ranks
            else _undefined("no_true_pairs_in_candidates")
        ),
        median_truth_candidate_rank_when_present=(
            _defined(float(np.median(present_ranks)))
            if present_ranks
            else _undefined("no_true_pairs_in_candidates")
        ),
    )


def _calibration_view(
    probabilities: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
    weighting: str,
) -> CalibrationView:
    if probabilities.size == 0:
        reason = "no_strict_candidate_pairs"
        empty_bins = [
            CalibrationBin(
                bin_index=index,
                lower_bound=index / ECE_BIN_COUNT,
                upper_bound=(index + 1) / ECE_BIN_COUNT,
                includes_upper_bound=index == ECE_BIN_COUNT - 1,
                pair_count=0,
                weight_sum=0.0,
                mean_probability=_undefined("no_pairs_in_bin"),
                observed_positive_rate=_undefined("no_pairs_in_bin"),
                absolute_calibration_gap=_undefined("no_pairs_in_bin"),
            )
            for index in range(ECE_BIN_COUNT)
        ]
        return CalibrationView(
            weighting=weighting,
            brier_score=_undefined(reason),
            log_loss=_undefined(reason),
            expected_calibration_error=_undefined(reason),
            bins=empty_bins,
        )

    weight_total = float(weights.sum())
    squared_error = (probabilities - labels) ** 2
    clipped = np.clip(probabilities, LOG_LOSS_EPSILON, 1.0 - LOG_LOSS_EPSILON)
    per_pair_log_loss = -(labels * np.log(clipped) + (1.0 - labels) * np.log1p(-clipped))
    brier = float(np.average(squared_error, weights=weights))
    log_loss = float(np.average(per_pair_log_loss, weights=weights))

    bin_indices = np.minimum((probabilities * ECE_BIN_COUNT).astype(int), ECE_BIN_COUNT - 1)
    bins: list[CalibrationBin] = []
    weighted_gap_sum = 0.0
    for index in range(ECE_BIN_COUNT):
        mask = bin_indices == index
        pair_count = int(mask.sum())
        bin_weight = float(weights[mask].sum())
        if pair_count == 0 or bin_weight == 0.0:
            mean_probability = _undefined("no_pairs_in_bin")
            observed_rate = _undefined("no_pairs_in_bin")
            gap = _undefined("no_pairs_in_bin")
        else:
            mean_value = float(np.average(probabilities[mask], weights=weights[mask]))
            observed_value = float(np.average(labels[mask], weights=weights[mask]))
            gap_value = abs(mean_value - observed_value)
            mean_probability = _defined(mean_value)
            observed_rate = _defined(observed_value)
            gap = _defined(gap_value)
            weighted_gap_sum += bin_weight * gap_value
        bins.append(
            CalibrationBin(
                bin_index=index,
                lower_bound=index / ECE_BIN_COUNT,
                upper_bound=(index + 1) / ECE_BIN_COUNT,
                includes_upper_bound=index == ECE_BIN_COUNT - 1,
                pair_count=pair_count,
                weight_sum=bin_weight,
                mean_probability=mean_probability,
                observed_positive_rate=observed_rate,
                absolute_calibration_gap=gap,
            )
        )

    return CalibrationView(
        weighting=weighting,
        brier_score=_defined(brier),
        log_loss=_defined(log_loss),
        expected_calibration_error=_defined(weighted_gap_sum / weight_total),
        bins=bins,
    )


def _pairwise_calibration_metrics(
    strict_cases: pd.DataFrame,
    truth_map: dict[str, str],
    candidates: pd.DataFrame,
) -> PairwiseCalibrationMetrics:
    strict_ids = set(strict_cases["case_id"])
    scored = candidates.loc[candidates["case_id"].isin(strict_ids)].copy()
    probabilities = pd.to_numeric(scored["posterior_match"]).to_numpy(dtype=float)
    labels = np.asarray(
        [
            float(truth_map.get(row.case_id) == row.right_id)
            for row in scored.itertuples(index=False)
        ],
        dtype=float,
    )
    micro_weights = np.ones(len(scored), dtype=float)
    if scored.empty:
        source_weights = np.asarray([], dtype=float)
        sources_with_pairs = 0
    else:
        candidate_counts = scored.groupby("case_id")["right_id"].transform("size")
        source_weights = 1.0 / candidate_counts.to_numpy(dtype=float)
        sources_with_pairs = int(scored["case_id"].nunique())

    return PairwiseCalibrationMetrics(
        scope=(
            "Binary calibration conditional on generated candidate pairs in complete strict "
            "components; not a categorical probability over candidates plus unmatched."
        ),
        scored_pairs=len(scored),
        positive_pairs=int(labels.sum()),
        negative_pairs=int(len(labels) - labels.sum()),
        sources_with_scored_pairs=sources_with_pairs,
        log_loss_epsilon=LOG_LOSS_EPSILON,
        average_precision=_average_precision(probabilities, labels),
        micro=_calibration_view(
            probabilities,
            labels,
            micro_weights,
            "one_equal_weight_per_candidate_pair",
        ),
        source_balanced=_calibration_view(
            probabilities,
            labels,
            source_weights,
            "one_equal_total_weight_per_source_with_candidates",
        ),
    )


def _average_precision(probabilities: np.ndarray, labels: np.ndarray) -> MetricValue:
    """Return tie-invariant average precision for binary candidate-pair labels."""

    if probabilities.size == 0:
        return _undefined("no_strict_candidate_pairs")
    positive_count = int(labels.sum())
    negative_count = int(labels.size - positive_count)
    if positive_count == 0:
        return _undefined("no_positive_candidate_pairs")
    if negative_count == 0:
        return _undefined("no_negative_candidate_pairs")

    order = np.argsort(-probabilities, kind="stable")
    ordered_probabilities = probabilities[order]
    ordered_labels = labels[order]
    true_positives = 0
    predicted_positives = 0
    average_precision = 0.0
    group_start = 0
    while group_start < len(ordered_probabilities):
        group_end = group_start + 1
        while (
            group_end < len(ordered_probabilities)
            and ordered_probabilities[group_end] == ordered_probabilities[group_start]
        ):
            group_end += 1
        group_positive_count = int(ordered_labels[group_start:group_end].sum())
        true_positives += group_positive_count
        predicted_positives += group_end - group_start
        precision = true_positives / predicted_positives
        average_precision += precision * group_positive_count / positive_count
        group_start = group_end
    return _defined(average_precision)


def _decision_metrics(
    strict_cases: pd.DataFrame,
    truth_map: dict[str, str],
    candidates: pd.DataFrame,
) -> DecisionMetrics:
    strict_ids = set(strict_cases["case_id"])
    selected = candidates.loc[candidates["selected"] & candidates["case_id"].isin(strict_ids)]
    selected_map = dict(zip(selected["case_id"], selected["right_id"], strict=True))

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    wrong_counterparts = 0
    selections_on_unmatched = 0
    positive_abstentions = 0
    for case in strict_cases.itertuples(index=False):
        selected_right = selected_map.get(case.case_id)
        if case.truth_state == "matched":
            if selected_right is None:
                false_negatives += 1
                positive_abstentions += 1
            elif selected_right == truth_map[case.case_id]:
                true_positives += 1
            else:
                false_positives += 1
                false_negatives += 1
                wrong_counterparts += 1
        elif selected_right is None:
            true_negatives += 1
        else:
            false_positives += 1
            selections_on_unmatched += 1

    strict_count = len(strict_cases)
    matched_count = int(strict_cases["truth_state"].eq("matched").sum())
    unmatched_count = int(strict_cases["truth_state"].eq("unmatched").sum())
    selected_count = len(selected)
    abstentions = strict_count - selected_count
    precision = _ratio(
        true_positives,
        true_positives + false_positives,
        "no_selected_pairs_in_strict_cases",
    )
    recall = _ratio(
        true_positives,
        true_positives + false_negatives,
        "no_strict_matched_cases",
    )
    f1_denominator = 2 * true_positives + false_positives + false_negatives

    return DecisionMetrics(
        strict_cases=strict_count,
        strict_matched_cases=matched_count,
        strict_unmatched_cases=unmatched_count,
        selected_pairs=selected_count,
        abstentions=abstentions,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        wrong_counterpart_selections=wrong_counterparts,
        selections_on_unmatched=selections_on_unmatched,
        positive_abstentions=positive_abstentions,
        precision=precision,
        recall=recall,
        f1=(
            _defined(2 * true_positives / f1_denominator)
            if f1_denominator
            else _undefined("no_positive_truth_or_selected_pairs")
        ),
        false_positive_rate_on_unmatched=_ratio(
            selections_on_unmatched,
            unmatched_count,
            "no_strict_unmatched_cases",
        ),
        exact_decision_accuracy=_ratio(
            true_positives + true_negatives,
            strict_count,
            "no_strict_cases",
        ),
        selection_rate=_ratio(selected_count, strict_count, "no_strict_cases"),
        abstention_rate=_ratio(abstentions, strict_count, "no_strict_cases"),
        positive_abstention_rate=_ratio(
            positive_abstentions,
            matched_count,
            "no_strict_matched_cases",
        ),
        negative_abstention_rate=_ratio(
            true_negatives,
            unmatched_count,
            "no_strict_unmatched_cases",
        ),
    )


def evaluate_external_benchmark(
    cases: pd.DataFrame,
    truth_pairs: pd.DataFrame,
    predicted_candidates: pd.DataFrame,
) -> ExternalBenchmarkEvaluation:
    """Validate and evaluate candidate generation, pair scores, and assignment decisions."""

    validate_external_benchmark(cases, truth_pairs, predicted_candidates)
    strict_cases = _strict_cases(cases)
    truth_map = _strict_truth_map(strict_cases, truth_pairs)

    counts = DatasetCounts(
        total_cases=len(cases),
        strict_cases=len(strict_cases),
        strict_matched_cases=int(strict_cases["truth_state"].eq("matched").sum()),
        strict_unmatched_cases=int(strict_cases["truth_state"].eq("unmatched").sum()),
        excluded_ambiguous_cases=int(cases["truth_state"].eq("ambiguous").sum()),
        excluded_unknown_cases=int(cases["truth_state"].eq("unknown").sum()),
        excluded_incomplete_cases=int(
            (cases["truth_state"].isin(["matched", "unmatched"]) & ~cases["truth_complete"]).sum()
        ),
        candidate_pairs=len(predicted_candidates),
        selected_pairs=int(predicted_candidates["selected"].sum()),
    )
    return ExternalBenchmarkEvaluation(
        counts=counts,
        candidate_generation=_candidate_generation_metrics(
            strict_cases,
            truth_map,
            predicted_candidates,
        ),
        pairwise_calibration=_pairwise_calibration_metrics(
            strict_cases,
            truth_map,
            predicted_candidates,
        ),
        decision=_decision_metrics(strict_cases, truth_map, predicted_candidates),
    )
