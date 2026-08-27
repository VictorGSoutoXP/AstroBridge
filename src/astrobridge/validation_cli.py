from __future__ import annotations

import argparse
import json
from pathlib import Path

from astrobridge.validation import run_synthetic_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic AstroBridge association benchmark."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--associations", type=int, default=200)
    parser.add_argument("--left-only", type=int, default=40)
    parser.add_argument("--right-only", type=int, default=40)
    parser.add_argument("--field-radius-deg", type=float, default=0.2)
    parser.add_argument("--candidate-radius-arcsec", type=float, default=2.0)
    parser.add_argument("--min-posterior", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    metrics = run_synthetic_benchmark(
        seed=args.seed,
        n_associations=args.associations,
        n_left_only=args.left_only,
        n_right_only=args.right_only,
        field_radius_deg=args.field_radius_deg,
        candidate_radius_arcsec=args.candidate_radius_arcsec,
        min_posterior=args.min_posterior,
    )
    payload = json.dumps(metrics.to_dict(), indent=2, sort_keys=True)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
