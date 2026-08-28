from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

FIELDS = (
    ("north_galactic_pole", "North Galactic Pole"),
    ("south_galactic_pole", "South Galactic Pole"),
    ("galactic_anticenter", "Galactic anticenter"),
    ("vela_plane", "Vela plane"),
    ("baade_window", "Baade window"),
    ("orion_nebula", "Orion nebula"),
    ("lmc_field", "LMC field"),
    ("m31_field", "M31 field"),
    ("hyades", "Hyades"),
    ("m4", "M4"),
)

COUNT_KEYS = (
    "gaia_sources",
    "allwise_sources",
    "candidate_pairs",
    "selected_associations",
    "official_associations",
    "clean_official_associations",
    "reference_in_candidate_set",
    "reference_missing_from_candidates",
    "agreements",
    "disagreements",
    "reference_candidate_not_selected",
    "selected_without_clean_reference",
)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if total == 0:
        return None
    if successes < 0 or successes > total:
        raise ValueError("successes must be between zero and total")
    proportion = successes / total
    z_squared = z**2
    denominator = 1.0 + z_squared / total
    center = (proportion + z_squared / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / total + z_squared / (4.0 * total**2))
        / denominator
    )
    return [center - half_width, center + half_width]


def descriptive_rates(values: list[float | None]) -> dict[str, float | int | None]:
    finite = [value for value in values if value is not None]
    if not finite:
        return {"fields_with_defined_rate": 0, "minimum": None, "maximum": None, "mean": None}
    return {
        "fields_with_defined_rate": len(finite),
        "minimum": min(finite),
        "maximum": max(finite),
        "mean": sum(finite) / len(finite),
    }


def aggregate_metrics(metrics: list[dict]) -> dict:
    aggregate = {key: sum(int(item[key]) for item in metrics) for key in COUNT_KEYS}
    clean = aggregate["clean_official_associations"]
    aggregate["candidate_coverage"] = (
        aggregate["reference_in_candidate_set"] / clean if clean else None
    )
    aggregate["same_counterpart_agreement"] = aggregate["agreements"] / clean if clean else None
    aggregate["candidate_coverage_wilson_95"] = wilson_interval(
        aggregate["reference_in_candidate_set"], clean
    )
    aggregate["same_counterpart_agreement_wilson_95"] = wilson_interval(
        aggregate["agreements"], clean
    )
    aggregate["field_candidate_coverage"] = descriptive_rates(
        [item["candidate_coverage"] for item in metrics]
    )
    aggregate["field_same_counterpart_agreement"] = descriptive_rates(
        [item["agreement_rate_on_clean_reference"] for item in metrics]
    )
    return aggregate


def secondary_metrics(payload: dict) -> dict:
    candidates = [
        item
        for item in payload.get("sensitivity", [])
        if math.isclose(float(item["min_posterior"]), 0.1)
        and math.isclose(float(item["expected_match_fraction"]), 0.7)
    ]
    if len(candidates) != 1:
        raise ValueError("expected exactly one secondary threshold=0.1, fraction=0.7 result")
    return candidates[0]["metrics"]


def comparison_diagnostics(path: Path, metrics: dict) -> tuple[dict, list[dict], list[float]]:
    """Validate a primary comparison CSV and return auditable diagnostics."""

    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    disagreements = [row for row in rows if row["status"].startswith("disagreement")]
    not_selected_posteriors = sorted(
        float(row["candidate_posterior"])
        for row in rows
        if row["status"] == "candidate_not_selected"
    )
    expected = {
        "agreement": int(metrics["agreements"]),
        "candidate_not_selected": int(metrics["reference_candidate_not_selected"]),
    }
    for status, count in expected.items():
        if status_counts.get(status, 0) != count:
            raise ValueError(
                f"{path.name}: CSV {status} count {status_counts.get(status, 0)} != {count}"
            )
    if len(disagreements) != int(metrics["disagreements"]):
        raise ValueError(f"{path.name}: disagreement count does not match JSON metrics")
    if len(rows) != int(metrics["clean_official_associations"]):
        raise ValueError(f"{path.name}: row count does not match clean official total")

    diagnostics = {
        "status_counts": status_counts,
        "candidate_not_selected_posterior": {
            "count": len(not_selected_posteriors),
            "minimum": min(not_selected_posteriors) if not_selected_posteriors else None,
            "median": (
                statistics.median(not_selected_posteriors) if not_selected_posteriors else None
            ),
            "maximum": max(not_selected_posteriors) if not_selected_posteriors else None,
        },
    }
    disagreement_details = [
        {
            key: row.get(key)
            for key in (
                "source_id",
                "reference_designation",
                "selected_designation",
                "candidate_posterior",
                "selected_posterior",
                "status",
            )
        }
        for row in disagreements
    ]
    return diagnostics, disagreement_details, not_selected_posteriors


def build_summary(input_dir: Path, expected_commit: str | None) -> dict:
    field_rows = []
    valid_primary = []
    valid_secondary = []
    commits = set()
    generated_times = []
    total_retries = 0
    all_not_selected_posteriors: list[float] = []
    all_disagreement_details: list[dict] = []

    for slug, label in FIELDS:
        path = input_dir / f"{slug}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        commit = payload["execution"]["git"]["commit"]
        commits.add(commit)
        if payload["execution"]["git"]["tracked_files_dirty"] is not False:
            raise ValueError(f"{slug}: tracked files were dirty during execution")
        if expected_commit is not None and commit != expected_commit:
            raise ValueError(f"{slug}: expected commit {expected_commit}, found {commit}")

        primary = payload["metrics"]
        secondary = secondary_metrics(payload)
        comparison_path = input_dir / f"{slug}.csv"
        diagnostics, disagreement_details, not_selected_posteriors = comparison_diagnostics(
            comparison_path, primary
        )
        all_not_selected_posteriors.extend(not_selected_posteriors)
        all_disagreement_details.extend(
            {"field": label, **detail} for detail in disagreement_details
        )
        truncated = bool(payload["input_manifest"]["gaia_query_limit_reached"])
        retries = int(payload["configuration"]["service_retry_count"])
        total_retries += retries
        generated_times.append(payload["generated_at_utc"])
        field_rows.append(
            {
                "slug": slug,
                "field": label,
                "artifact": path.as_posix(),
                "comparison_artifact": comparison_path.as_posix(),
                "generated_at_utc": payload["generated_at_utc"],
                "truncated": truncated,
                "service_retry_count": retries,
                "primary": primary,
                "primary_diagnostics": diagnostics,
                "secondary_threshold_0_1": secondary,
            }
        )
        if not truncated:
            valid_primary.append(primary)
            valid_secondary.append(secondary)

    if len(commits) != 1:
        raise ValueError(f"field artifacts contain multiple commits: {sorted(commits)}")

    primary_aggregate = aggregate_metrics(valid_primary)
    secondary_aggregate = aggregate_metrics(valid_secondary)
    coverage_pass = primary_aggregate["candidate_coverage"] is not None and (
        primary_aggregate["candidate_coverage"] >= 0.95
    )
    agreement_interval = primary_aggregate["same_counterpart_agreement_wilson_95"]
    agreement_pass = agreement_interval is not None and agreement_interval[0] >= 0.90
    different_counterparts = primary_aggregate["disagreements"]
    all_not_selected_posteriors.sort()

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "input_directory": input_dir.as_posix(),
        "implementation_commit": next(iter(commits)),
        "field_count": len(field_rows),
        "aggregate_field_count": len(valid_primary),
        "truncated_field_count": sum(row["truncated"] for row in field_rows),
        "total_service_retry_count": total_retries,
        "artifact_generation_time_range_utc": [min(generated_times), max(generated_times)],
        "fields": field_rows,
        "primary": primary_aggregate,
        "primary_candidate_not_selected_posterior": {
            "count": len(all_not_selected_posteriors),
            "minimum": (min(all_not_selected_posteriors) if all_not_selected_posteriors else None),
            "median": (
                statistics.median(all_not_selected_posteriors)
                if all_not_selected_posteriors
                else None
            ),
            "maximum": (max(all_not_selected_posteriors) if all_not_selected_posteriors else None),
        },
        "primary_disagreement_details": all_disagreement_details,
        "secondary_threshold_0_1": secondary_aggregate,
        "decision_rule": {
            "candidate_coverage_at_least_0_95": coverage_pass,
            "agreement_wilson_lower_at_least_0_90": agreement_pass,
            "different_counterparts_to_inspect": different_counterparts,
            "all_different_counterparts_inspected": different_counterparts == 0,
            "engineering_comparator_passed": (
                coverage_pass and agreement_pass and different_counterparts == 0
            ),
        },
        "interpretation": (
            "Descriptive agreement with the official Gaia DR3-AllWISE algorithm; not "
            "ground-truth accuracy or all-sky performance."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate the frozen Gaia-AllWISE field study.")
    parser.add_argument("--input-dir", type=Path, default=Path("reports/benchmark_data"))
    parser.add_argument("--expected-commit")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = build_summary(args.input_dir, args.expected_commit)
    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
