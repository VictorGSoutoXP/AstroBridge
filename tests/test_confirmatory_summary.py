import pytest

from scripts.summarize_gaia_allwise_confirmatory import (
    aggregate_metrics,
    comparison_diagnostics,
    wilson_interval,
)


def _metrics(*, clean, candidates, agreements, coverage, agreement_rate):
    return {
        "gaia_sources": 10,
        "allwise_sources": 9,
        "candidate_pairs": 8,
        "selected_associations": agreements,
        "official_associations": clean,
        "clean_official_associations": clean,
        "reference_in_candidate_set": candidates,
        "reference_missing_from_candidates": clean - candidates,
        "agreements": agreements,
        "disagreements": 0,
        "reference_candidate_not_selected": candidates - agreements,
        "selected_without_clean_reference": 0,
        "candidate_coverage": coverage,
        "agreement_rate_on_clean_reference": agreement_rate,
    }


def test_wilson_interval_handles_boundaries_and_invalid_counts():
    lower, upper = wilson_interval(10, 10)
    assert lower == pytest.approx(0.7224672, rel=1e-6)
    assert upper == pytest.approx(1.0)
    assert wilson_interval(0, 0) is None
    with pytest.raises(ValueError, match="between zero and total"):
        wilson_interval(11, 10)


def test_aggregate_metrics_reports_micro_and_macro_rates():
    metrics = [
        _metrics(clean=10, candidates=10, agreements=8, coverage=1.0, agreement_rate=0.8),
        _metrics(clean=0, candidates=0, agreements=0, coverage=None, agreement_rate=None),
    ]

    result = aggregate_metrics(metrics)

    assert result["candidate_coverage"] == pytest.approx(1.0)
    assert result["same_counterpart_agreement"] == pytest.approx(0.8)
    assert result["field_same_counterpart_agreement"] == {
        "fields_with_defined_rate": 1,
        "minimum": 0.8,
        "maximum": 0.8,
        "mean": 0.8,
    }


def test_comparison_diagnostics_validates_counts_and_collects_posteriors(tmp_path):
    comparison = tmp_path / "field.csv"
    comparison.write_text(
        "source_id,reference_designation,selected_designation,candidate_posterior,"
        "selected_posterior,status\n"
        "1,A,A,0.9,0.9,agreement\n"
        "2,B,,0.2,,candidate_not_selected\n",
        encoding="utf-8",
    )
    metrics = _metrics(
        clean=2,
        candidates=2,
        agreements=1,
        coverage=1.0,
        agreement_rate=0.5,
    )

    diagnostics, disagreements, posteriors = comparison_diagnostics(comparison, metrics)

    assert diagnostics["status_counts"] == {"agreement": 1, "candidate_not_selected": 1}
    assert disagreements == []
    assert posteriors == [0.2]
