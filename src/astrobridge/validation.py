from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from astrobridge.bayes import cone_solid_angle_sr
from astrobridge.matching import probabilistic_crossmatch


@dataclass(frozen=True)
class AssociationMetrics:
    """Metrics for a benchmark with known one-to-one associations."""

    seed: int
    field_radius_deg: float
    candidate_radius_arcsec: float
    min_posterior: float
    left_sources: int
    right_sources: int
    true_associations: int
    selected_associations: int
    correct_associations: int
    incorrect_associations: int
    missed_associations: int
    precision: float
    recall: float
    f1: float
    candidate_pairs: int
    prior_odds: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _sample_cone_offsets(
    rng: np.random.Generator, count: int, radius_deg: float
) -> tuple[np.ndarray, np.ndarray]:
    radial_deg = radius_deg * np.sqrt(rng.uniform(size=count))
    angle = rng.uniform(0.0, 2.0 * np.pi, size=count)
    return radial_deg * np.cos(angle), radial_deg * np.sin(angle)


def _apply_tangent_offsets(
    ra_deg: np.ndarray,
    dec_deg: np.ndarray,
    east_arcsec: np.ndarray,
    north_arcsec: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    shifted_ra = ra_deg + east_arcsec / (3600.0 * np.cos(np.deg2rad(dec_deg)))
    shifted_dec = dec_deg + north_arcsec / 3600.0
    return shifted_ra % 360.0, shifted_dec


def synthetic_catalogs(
    *,
    n_associations: int = 200,
    n_left_only: int = 40,
    n_right_only: int = 40,
    center_ra_deg: float = 120.0,
    center_dec_deg: float = -30.0,
    field_radius_deg: float = 0.2,
    left_sigma_arcsec: float = 0.05,
    right_sigma_arcsec: float = 0.30,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate two catalogs with traceable true associations and contaminants."""

    if n_associations <= 0:
        raise ValueError("n_associations must be positive")
    if n_left_only < 0 or n_right_only < 0:
        raise ValueError("contaminant counts must be non-negative")
    if field_radius_deg <= 0:
        raise ValueError("field_radius_deg must be positive")

    rng = np.random.default_rng(seed)
    east_deg, north_deg = _sample_cone_offsets(rng, n_associations, field_radius_deg)
    true_ra = center_ra_deg + east_deg / np.cos(np.deg2rad(center_dec_deg))
    true_dec = center_dec_deg + north_deg

    left_ra, left_dec = _apply_tangent_offsets(
        true_ra,
        true_dec,
        rng.normal(0.0, left_sigma_arcsec, n_associations),
        rng.normal(0.0, left_sigma_arcsec, n_associations),
    )
    right_ra, right_dec = _apply_tangent_offsets(
        true_ra,
        true_dec,
        rng.normal(0.0, right_sigma_arcsec, n_associations),
        rng.normal(0.0, right_sigma_arcsec, n_associations),
    )

    left = pd.DataFrame(
        {
            "source_id": np.arange(n_associations, dtype=int),
            "ra": left_ra,
            "dec": left_dec,
            "position_sigma_arcsec": left_sigma_arcsec,
        }
    )
    right = pd.DataFrame(
        {
            "designation": [f"true-{index}" for index in range(n_associations)],
            "ra": right_ra,
            "dec": right_dec,
            "position_sigma_arcsec": right_sigma_arcsec,
        }
    )

    if n_left_only:
        east_deg, north_deg = _sample_cone_offsets(rng, n_left_only, field_radius_deg)
        left_only = pd.DataFrame(
            {
                "source_id": np.arange(n_associations, n_associations + n_left_only, dtype=int),
                "ra": center_ra_deg + east_deg / np.cos(np.deg2rad(center_dec_deg)),
                "dec": center_dec_deg + north_deg,
                "position_sigma_arcsec": left_sigma_arcsec,
            }
        )
        left = pd.concat([left, left_only], ignore_index=True)

    if n_right_only:
        east_deg, north_deg = _sample_cone_offsets(rng, n_right_only, field_radius_deg)
        right_only = pd.DataFrame(
            {
                "designation": [f"right-only-{index}" for index in range(n_right_only)],
                "ra": center_ra_deg + east_deg / np.cos(np.deg2rad(center_dec_deg)),
                "dec": center_dec_deg + north_deg,
                "position_sigma_arcsec": right_sigma_arcsec,
            }
        )
        right = pd.concat([right, right_only], ignore_index=True)

    return left, right


def run_synthetic_benchmark(
    *,
    n_associations: int = 200,
    n_left_only: int = 40,
    n_right_only: int = 40,
    field_radius_deg: float = 0.2,
    candidate_radius_arcsec: float = 2.0,
    min_posterior: float = 0.5,
    seed: int = 42,
) -> AssociationMetrics:
    """Run a deterministic end-to-end association benchmark."""

    left, right = synthetic_catalogs(
        n_associations=n_associations,
        n_left_only=n_left_only,
        n_right_only=n_right_only,
        field_radius_deg=field_radius_deg,
        seed=seed,
    )
    expected_fraction = n_associations / min(len(left), len(right))
    result = probabilistic_crossmatch(
        left,
        right,
        left_sigma_arcsec=left["position_sigma_arcsec"],
        right_sigma_arcsec=right["position_sigma_arcsec"],
        candidate_radius_arcsec=candidate_radius_arcsec,
        min_posterior=min_posterior,
        area_solid_angle_sr=cone_solid_angle_sr(field_radius_deg),
        expected_match_fraction=expected_fraction,
    )

    correct = 0
    for row in result.matches.itertuples(index=False):
        if row.wise_designation == f"true-{row.gaia_source_id}":
            correct += 1
    selected = len(result.matches)
    incorrect = selected - correct
    missed = n_associations - correct
    precision = correct / selected if selected else 0.0
    recall = correct / n_associations
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return AssociationMetrics(
        seed=seed,
        field_radius_deg=field_radius_deg,
        candidate_radius_arcsec=candidate_radius_arcsec,
        min_posterior=min_posterior,
        left_sources=len(left),
        right_sources=len(right),
        true_associations=n_associations,
        selected_associations=selected,
        correct_associations=correct,
        incorrect_associations=incorrect,
        missed_associations=missed,
        precision=precision,
        recall=recall,
        f1=f1,
        candidate_pairs=len(result.candidates),
        prior_odds=result.prior_odds,
    )
