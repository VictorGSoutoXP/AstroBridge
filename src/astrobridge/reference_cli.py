from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from astrobridge import __version__
from astrobridge.astrometry import effective_circular_sigma_arcsec, propagate_gaia_position
from astrobridge.bayes import cone_solid_angle_sr
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
    parser.add_argument("--output", type=Path)
    parser.add_argument("--details-output", type=Path)
    args = parser.parse_args()

    wise_radius = expanded_catalog_radius_deg(args.radius, args.candidate_radius_arcsec)
    gaia = fetch_gaia_dr3(args.ra, args.dec, args.radius, limit=args.gaia_limit)
    gaia_epoch = propagate_gaia_position(gaia, from_epoch=2016.0, to_epoch=2010.5)
    gaia_matchable = gaia_epoch.loc[gaia_epoch["proper_motion_available"]].reset_index(drop=True)
    allwise = fetch_allwise(args.ra, args.dec, wise_radius)
    allwise_sigma = effective_circular_sigma_arcsec(allwise["sigra"], allwise["sigdec"])

    reference = fetch_gaia_allwise_best_neighbours(gaia_matchable["source_id"])

    def run_match(min_posterior: float, expected_fraction: float):
        return probabilistic_crossmatch(
            gaia_matchable,
            allwise,
            left_sigma_arcsec=gaia_matchable["position_sigma_arcsec"],
            right_sigma_arcsec=allwise_sigma,
            left_ra="ra_epoch",
            left_dec="dec_epoch",
            candidate_radius_arcsec=args.candidate_radius_arcsec,
            min_posterior=min_posterior,
            area_solid_angle_sr=cone_solid_angle_sr(wise_radius),
            expected_match_fraction=expected_fraction,
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
            "candidate_radius_arcsec": args.candidate_radius_arcsec,
            "min_posterior": args.min_posterior,
            "expected_match_fraction": args.expected_match_fraction,
            "gaia_limit": args.gaia_limit,
        },
        "input_manifest": {
            "gaia_source_ids_sha256": identifier_sha256(gaia_matchable["source_id"]),
            "allwise_designations_sha256": identifier_sha256(allwise["designation"]),
            "official_reference_rows": len(reference),
            "gaia_query_limit_reached": len(gaia) >= args.gaia_limit,
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
