from __future__ import annotations

import argparse
from pathlib import Path

from astrobridge.astrometry import crossmatch_nearest, propagate_gaia_position
from astrobridge.bayes import budavari_szalay_bayes_factor, posterior_from_bayes_factor
from astrobridge.data import fetch_allwise, fetch_gaia_dr3
from astrobridge.plots import plot_cmd, plot_distance_distribution
from astrobridge.simbad import add_simbad_flags


def run_pipeline(
    ra: float,
    dec: float,
    radius: float,
    out: str,
    threshold_arcsec: float = 2.0,
    gaia_limit: int = 20000,
    simbad_limit: int = 100,
) -> None:
    output_path = Path(out)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gaia = fetch_gaia_dr3(ra=ra, dec=dec, radius=radius, limit=gaia_limit)
    wise = fetch_allwise(ra=ra, dec=dec, radius=radius)

    gaia_epoch = propagate_gaia_position(gaia, from_epoch=2016.0, to_epoch=2010.5)

    matches_raw = crossmatch_nearest(
        left_df=gaia,
        right_df=wise,
        left_ra="ra",
        left_dec="dec",
        threshold_arcsec=threshold_arcsec,
    )

    matches_pm = crossmatch_nearest(
        left_df=gaia_epoch,
        right_df=wise,
        left_ra="ra_epoch",
        left_dec="dec_epoch",
        threshold_arcsec=threshold_arcsec,
    )

    if not matches_pm.empty:
        matches_pm["bayes_factor_pos"] = budavari_szalay_bayes_factor(
            matches_pm["distance_arcsec"],
            sigma1_arcsec=0.1,
            sigma2_arcsec=0.5,
        )
        matches_pm["posterior_match"] = posterior_from_bayes_factor(
            matches_pm["bayes_factor_pos"],
            prior_match_probability=0.5,
        )

    matches_pm = add_simbad_flags(
        matches_pm,
        ra_col="gaia_ra",
        dec_col="gaia_dec",
        radius_arcsec=2.0,
        limit=simbad_limit,
    )

    matches_pm.to_csv(output_path, index=False)

    fig_dir = Path("reports/figures")
    plot_cmd(matches_pm, fig_dir / "cmd_gaia.png")
    plot_distance_distribution(matches_pm, fig_dir / "distance_distribution.png")

    print(f"Total Gaia: {len(gaia)}")
    print(f"Total WISE: {len(wise)}")
    print(f"Matches sem correção PM: {len(matches_raw)}")
    print(f"Matches com correção PM: {len(matches_pm)}")

    if "known_in_simbad" in matches_pm.columns:
        known = matches_pm["known_in_simbad"].fillna(0).sum()
        checked = matches_pm["known_in_simbad"].notna().sum()
        print(f"Consultados no SIMBAD: {checked}")
        print(f"Conhecidos no SIMBAD: {int(known)}")

    print(f"Arquivo salvo em: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ra", type=float, required=True)
    parser.add_argument("--dec", type=float, required=True)
    parser.add_argument("--radius", type=float, required=True)
    parser.add_argument("--out", type=str, default="data/processed/astro_matches.csv")
    parser.add_argument("--threshold-arcsec", type=float, default=2.0)
    parser.add_argument("--gaia-limit", type=int, default=20000)
    parser.add_argument("--simbad-limit", type=int, default=100)
    args = parser.parse_args()

    run_pipeline(
        ra=args.ra,
        dec=args.dec,
        radius=args.radius,
        out=args.out,
        threshold_arcsec=args.threshold_arcsec,
        gaia_limit=args.gaia_limit,
        simbad_limit=args.simbad_limit,
    )


if __name__ == "__main__":
    main()
