from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from astrobridge import __version__
from astrobridge.astrometry import (
    count_rows_within_cone,
    effective_circular_sigma_arcsec,
    maximum_radius_from_center_deg,
    propagate_gaia_position,
)
from astrobridge.bayes import catalog_prior_odds, cone_solid_angle_sr
from astrobridge.data import (
    fetch_allwise,
    fetch_gaia_allwise_best_neighbours,
    fetch_gaia_dr3,
)
from astrobridge.matching import probabilistic_crossmatch
from astrobridge.pipeline import expanded_catalog_radius_deg
from astrobridge.reference_validation import (
    evaluate_gaia_allwise_reference,
    gaia_allwise_reference_comparison,
)


def identifier_sha256(values) -> str:
    """Hash a sorted identifier manifest without embedding the identifiers in output."""

    normalized = "\n".join(sorted(str(value).strip() for value in values))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def dataframe_sha256(frame) -> str:
    """Hash dataframe values independent of row and column ordering."""

    columns = sorted(frame.columns)
    if not columns:
        return hashlib.sha256(b"<no-columns>\n").hexdigest()
    serialized = frame.loc[:, columns].to_csv(
        index=False,
        lineterminator="\n",
        float_format="%.17g",
    )
    header, *rows = serialized.splitlines()
    canonical = "\n".join([header, *sorted(rows)]) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def git_provenance() -> dict[str, str | bool | None]:
    """Return revision and tracked-file state when running from a checkout."""

    repository_hint = Path(__file__).resolve().parents[2]
    try:
        revision = subprocess.run(
            ["git", "-C", str(repository_hint), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        tracked_diff = subprocess.run(
            ["git", "-C", str(repository_hint), "diff-index", "--quiet", "HEAD", "--"],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return {"commit": None, "tracked_files_dirty": None}
    dirty = None if tracked_diff.returncode not in (0, 1) else tracked_diff.returncode == 1
    return {"commit": revision.stdout.strip() or None, "tracked_files_dirty": dirty}


def dependency_versions() -> dict[str, str]:
    """Return versions of the numerical and catalog-query runtime."""

    packages = ("numpy", "pandas", "scipy", "astropy", "astroquery")
    return {package: importlib.metadata.version(package) for package in packages}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare AstroBridge with clean official Gaia DR3-AllWISE associations."
    )
    parser.add_argument("--ra", type=float, required=True)
    parser.add_argument("--dec", type=float, required=True)
    parser.add_argument("--radius", type=float, required=True)
    parser.add_argument("--candidate-radius-arcsec", type=float, default=2.0)
    parser.add_argument("--min-posterior", type=float, default=0.5)
    parser.add_argument("--expected-match-fraction", type=float, default=0.7)
    parser.add_argument("--posterior-grid", nargs="+", type=float)
    parser.add_argument("--expected-fraction-grid", nargs="+", type=float)
    parser.add_argument("--gaia-limit", type=int, default=20000)
    parser.add_argument("--service-retry-count", type=int, default=0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--details-output", type=Path)
    args = parser.parse_args()
    if args.service_retry_count < 0:
        parser.error("--service-retry-count must be non-negative")

    gaia = fetch_gaia_dr3(args.ra, args.dec, args.radius, limit=args.gaia_limit)
    gaia_epoch = propagate_gaia_position(gaia, from_epoch=2016.0, to_epoch=2010.5)
    gaia_matchable = gaia_epoch.loc[gaia_epoch["proper_motion_available"]].reset_index(drop=True)
    propagated_radius = maximum_radius_from_center_deg(
        gaia_matchable,
        args.ra,
        args.dec,
        ra_col="ra_epoch",
        dec_col="dec_epoch",
    )
    wise_radius = expanded_catalog_radius_deg(
        max(args.radius, propagated_radius), args.candidate_radius_arcsec
    )
    allwise = fetch_allwise(args.ra, args.dec, wise_radius)
    allwise_sigma = effective_circular_sigma_arcsec(allwise["sigra"], allwise["sigdec"])
    allwise_prior_count = count_rows_within_cone(
        allwise,
        args.ra,
        args.dec,
        args.radius,
    )
    prior_area = cone_solid_angle_sr(args.radius)

    reference = fetch_gaia_allwise_best_neighbours(gaia_matchable["source_id"])

    def run_match(min_posterior: float, expected_fraction: float):
        prior_odds = (
            catalog_prior_odds(
                len(gaia_matchable),
                allwise_prior_count,
                prior_area,
                expected_match_fraction=expected_fraction,
            )
            if len(gaia_matchable) and allwise_prior_count
            else 0.0
        )
        return probabilistic_crossmatch(
            gaia_matchable,
            allwise,
            left_sigma_arcsec=gaia_matchable["position_sigma_arcsec"],
            right_sigma_arcsec=allwise_sigma,
            left_ra="ra_epoch",
            left_dec="dec_epoch",
            candidate_radius_arcsec=args.candidate_radius_arcsec,
            min_posterior=min_posterior,
            prior_odds=prior_odds,
        )

    result = run_match(args.min_posterior, args.expected_match_fraction)
    metrics = evaluate_gaia_allwise_reference(
        result,
        gaia_matchable,
        allwise,
        reference,
    )
    comparison = gaia_allwise_reference_comparison(
        result,
        gaia_matchable,
        allwise,
        reference,
    )
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "astrobridge_version": __version__,
        "configuration": {
            "ra_deg": args.ra,
            "dec_deg": args.dec,
            "gaia_radius_deg": args.radius,
            "allwise_radius_deg": wise_radius,
            "propagated_gaia_max_radius_deg": propagated_radius,
            "candidate_radius_arcsec": args.candidate_radius_arcsec,
            "min_posterior": args.min_posterior,
            "expected_match_fraction": args.expected_match_fraction,
            "gaia_limit": args.gaia_limit,
            "service_retry_count": args.service_retry_count,
        },
        "input_manifest": {
            "gaia_source_ids_sha256": identifier_sha256(gaia_matchable["source_id"]),
            "allwise_designations_sha256": identifier_sha256(allwise["designation"]),
            "gaia_content_sha256": dataframe_sha256(gaia_matchable),
            "allwise_content_sha256": dataframe_sha256(allwise),
            "official_reference_content_sha256": dataframe_sha256(reference),
            "candidate_pairs_content_sha256": dataframe_sha256(result.candidates),
            "selected_associations_content_sha256": dataframe_sha256(result.matches),
            "comparison_content_sha256": dataframe_sha256(comparison),
            "official_reference_rows": len(reference),
            "gaia_rows_downloaded": len(gaia),
            "gaia_matchable_sources": len(gaia_matchable),
            "allwise_rows_downloaded": len(allwise),
            "allwise_sources_in_prior_footprint": allwise_prior_count,
            "gaia_query_limit_reached": bool(gaia.attrs.get("gaia_query_limit_reached", False)),
        },
        "prior": {
            "model": "finite-footprint odds scaled by area/(4*pi) for all-sky Bayes factor",
            "common_footprint_radius_deg": args.radius,
            "common_footprint_solid_angle_sr": prior_area,
            "gaia_sources": len(gaia_matchable),
            "allwise_sources": allwise_prior_count,
            "effective_odds": result.prior_odds,
        },
        "execution": {
            "git": git_provenance(),
            "python_version": platform.python_version(),
            "dependency_versions": dependency_versions(),
            "gaia_adql": gaia.attrs.get("adql_query"),
            "official_reference_adql": reference.attrs.get("adql_queries", []),
            "allwise_query": {
                "service": "IRSA",
                "catalog": "allwise_p3as_psd",
                "spatial": "Cone",
                "ra_deg": args.ra,
                "dec_deg": args.dec,
                "radius_deg": wise_radius,
            },
        },
        "metrics": metrics.to_dict(),
        "interpretation": "Agreement with an external algorithm, not ground-truth accuracy.",
        "reference": {
            "table": "gaiadr3.allwise_best_neighbour",
            "doi": "10.17876/gaia/dr.3/29",
            "clean_subset": "xm_flag == 8 and number_of_neighbours == 1 and number_of_mates == 0",
        },
    }
    if args.posterior_grid or args.expected_fraction_grid:
        posterior_values = args.posterior_grid or [args.min_posterior]
        fraction_values = args.expected_fraction_grid or [args.expected_match_fraction]
        sensitivity = []
        for expected_fraction in fraction_values:
            for min_posterior in posterior_values:
                grid_result = run_match(min_posterior, expected_fraction)
                grid_metrics = evaluate_gaia_allwise_reference(
                    grid_result,
                    gaia_matchable,
                    allwise,
                    reference,
                )
                sensitivity.append(
                    {
                        "min_posterior": min_posterior,
                        "expected_match_fraction": expected_fraction,
                        "prior_odds": grid_result.prior_odds,
                        "metrics": grid_metrics.to_dict(),
                    }
                )
        payload["sensitivity"] = sensitivity
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    if args.details_output:
        args.details_output.parent.mkdir(parents=True, exist_ok=True)
        comparison.to_csv(args.details_output, index=False)


if __name__ == "__main__":
    main()
