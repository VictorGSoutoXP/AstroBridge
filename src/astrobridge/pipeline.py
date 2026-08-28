from __future__ import annotations

import argparse
from pathlib import Path

from astrobridge.astrometry import (
    count_rows_within_cone,
    crossmatch_nearest,
    effective_circular_sigma_arcsec,
    maximum_radius_from_center_deg,
    propagate_gaia_position,
)
from astrobridge.bayes import catalog_prior_odds, cone_solid_angle_sr
from astrobridge.data import fetch_allwise, fetch_gaia_dr3
from astrobridge.matching import probabilistic_crossmatch
from astrobridge.plots import plot_cmd, plot_distance_distribution
from astrobridge.simbad import add_simbad_flags


def expanded_catalog_radius_deg(radius_deg: float, candidate_radius_arcsec: float) -> float:
    """Expand a secondary-catalog cone so edge sources remain eligible candidates."""

    if radius_deg <= 0 or radius_deg > 180:
        raise ValueError("radius_deg must be in the interval (0, 180]")
    if candidate_radius_arcsec <= 0:
        raise ValueError("candidate_radius_arcsec must be positive")
    expanded = radius_deg + candidate_radius_arcsec / 3600.0
    if expanded > 180:
        raise ValueError("expanded catalog radius cannot exceed 180 degrees")
    return expanded


def run_pipeline(
    ra: float,
    dec: float,
    radius: float,
    out: str,
    threshold_arcsec: float = 2.0,
    min_posterior: float = 0.5,
    expected_match_fraction: float = 0.7,
    gaia_limit: int = 20000,
    simbad_limit: int = 100,
) -> None:
    if not 0.0 < min_posterior < 1.0:
        raise ValueError("min_posterior must be between zero and one")
    if not 0.0 <= expected_match_fraction <= 1.0:
        raise ValueError("expected_match_fraction must be between zero and one")
    if gaia_limit <= 0:
        raise ValueError("gaia_limit must be positive")
    if simbad_limit < 0:
        raise ValueError("simbad_limit must be non-negative")

    output_path = Path(out)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gaia = fetch_gaia_dr3(ra=ra, dec=dec, radius=radius, limit=gaia_limit)
    gaia_epoch = propagate_gaia_position(gaia, from_epoch=2016.0, to_epoch=2010.5)
    gaia_with_motion = gaia_epoch.loc[gaia_epoch["proper_motion_available"]].reset_index(drop=True)

    propagated_radius = maximum_radius_from_center_deg(
        gaia_with_motion,
        ra,
        dec,
        ra_col="ra_epoch",
        dec_col="dec_epoch",
    )
    wise_radius = expanded_catalog_radius_deg(max(radius, propagated_radius), threshold_arcsec)
    wise = fetch_allwise(ra=ra, dec=dec, radius=wise_radius)
    wise_sigma = effective_circular_sigma_arcsec(wise["sigra"], wise["sigdec"])
    wise_prior_count = count_rows_within_cone(wise, ra, dec, radius)
    prior_odds = (
        catalog_prior_odds(
            len(gaia_with_motion),
            wise_prior_count,
            cone_solid_angle_sr(radius),
            expected_match_fraction=expected_match_fraction,
        )
        if len(gaia_with_motion) and wise_prior_count
        else 0.0
    )

    matches_raw = crossmatch_nearest(
        left_df=gaia,
        right_df=wise,
        left_ra="ra",
        left_dec="dec",
        threshold_arcsec=threshold_arcsec,
    )

    match_result = probabilistic_crossmatch(
        gaia_with_motion,
        wise,
        left_sigma_arcsec=gaia_with_motion["position_sigma_arcsec"],
        right_sigma_arcsec=wise_sigma,
        left_ra="ra_epoch",
        left_dec="dec_epoch",
        candidate_radius_arcsec=threshold_arcsec,
        min_posterior=min_posterior,
        prior_odds=prior_odds,
    )
    matches_pm = match_result.matches

    matches_pm = add_simbad_flags(
        matches_pm,
        ra_col="gaia_ra",
        dec_col="gaia_dec",
        radius_arcsec=2.0,
        limit=simbad_limit,
    )

    matches_pm.to_csv(output_path, index=False)

    if not matches_pm.empty:
        fig_dir = Path("reports/figures")
        plot_cmd(matches_pm, fig_dir / "cmd_gaia.png")
        plot_distance_distribution(matches_pm, fig_dir / "distance_distribution.png")

    print(f"Total Gaia: {len(gaia)}")
    print(f"Gaia com movimento próprio utilizável: {len(gaia_with_motion)}")
    print(f"Total WISE: {len(wise)}")
    print(f"Matches sem correção PM: {len(matches_raw)}")
    print(f"Pares candidatos com correção PM: {len(match_result.candidates)}")
    print(f"Matches probabilísticos únicos: {len(matches_pm)}")
    print(f"Prior odds usado: {match_result.prior_odds:.6g}")

    if "known_in_simbad" in matches_pm.columns:
        known = matches_pm["known_in_simbad"].eq(1).sum()
        checked = matches_pm["known_in_simbad"].notna().sum()
        failed = (matches_pm["simbad_query_status"] == "error").sum()
        print(f"Consultados no SIMBAD: {checked}")
        print(f"Conhecidos no SIMBAD: {int(known)}")
        print(f"Falhas de consulta no SIMBAD: {int(failed)}")

    print(f"Arquivo salvo em: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ra", type=float, required=True)
    parser.add_argument("--dec", type=float, required=True)
    parser.add_argument("--radius", type=float, required=True)
    parser.add_argument("--out", type=str, default="data/processed/astro_matches.csv")
    parser.add_argument("--threshold-arcsec", type=float, default=2.0)
    parser.add_argument("--min-posterior", type=float, default=0.5)
    parser.add_argument("--expected-match-fraction", type=float, default=0.7)
    parser.add_argument("--gaia-limit", type=int, default=20000)
    parser.add_argument("--simbad-limit", type=int, default=100)
    args = parser.parse_args()

    run_pipeline(
        ra=args.ra,
        dec=args.dec,
        radius=args.radius,
        out=args.out,
        threshold_arcsec=args.threshold_arcsec,
        min_posterior=args.min_posterior,
        expected_match_fraction=args.expected_match_fraction,
        gaia_limit=args.gaia_limit,
        simbad_limit=args.simbad_limit,
    )


if __name__ == "__main__":
    main()
