from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from astrobridge.astrometry import candidate_pairs_within_radius
from astrobridge.bayes import (
    budavari_szalay_bayes_factor,
    catalog_prior_odds,
    posterior_from_bayes_factor,
)


@dataclass(frozen=True)
class CrossmatchResult:
    """Resolved matches, all scored candidates, and the prior used."""

    matches: pd.DataFrame
    candidates: pd.DataFrame
    prior_odds: float


def _source_values(values: float | pd.Series | np.ndarray, size: int, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        array = np.full(size, float(array), dtype=float)
    if array.shape != (size,):
        raise ValueError(f"{name} must be scalar or have one value per catalog row")
    if np.any(~np.isfinite(array)) or np.any(array <= 0):
        raise ValueError(f"{name} must contain finite positive values")
    return array


def resolve_unique_matches(
    candidates: pd.DataFrame,
    score_col: str = "posterior_match",
    min_score: float = 0.5,
) -> pd.DataFrame:
    """Resolve one-to-one associations with an unmatched option.

    The bipartite candidate graph is split into connected components, keeping
    memory proportional to local ambiguity rather than total catalog size.
    Each real edge has utility ``logit(score) - logit(min_score)`` and each
    left source receives a private zero-utility dummy. This maximizes joint
    match odds while making ``min_score`` the match-versus-unmatched decision
    boundary. A real candidate must meet or exceed that threshold.
    """

    required = {"left_index", "right_index", score_col}
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"candidates missing columns: {sorted(missing)}")
    if not 0.0 < min_score < 1.0:
        raise ValueError("min_score must be between zero and one")
    if candidates.empty:
        return candidates.copy()

    scores = pd.to_numeric(candidates[score_col], errors="coerce")
    finite_scores = scores[np.isfinite(scores)]
    if ((finite_scores < 0.0) | (finite_scores > 1.0)).any():
        raise ValueError(f"{score_col} must contain probabilities between zero and one")
    eligible = candidates.loc[np.isfinite(scores) & (scores >= min_score)].copy()
    if eligible.empty:
        return eligible.reset_index(drop=True)

    eligible[score_col] = pd.to_numeric(eligible[score_col], errors="raise")
    eligible = (
        eligible.sort_values(score_col, ascending=False)
        .drop_duplicates(["left_index", "right_index"], keep="first")
        .reset_index(drop=True)
    )

    left_to_right: dict[int, set[int]] = {}
    right_to_left: dict[int, set[int]] = {}
    for left, right in zip(eligible["left_index"], eligible["right_index"], strict=True):
        left_int = int(left)
        right_int = int(right)
        left_to_right.setdefault(left_int, set()).add(right_int)
        right_to_left.setdefault(right_int, set()).add(left_int)

    selected_rows: list[int] = []
    unvisited_left = set(left_to_right)
    while unvisited_left:
        seed = unvisited_left.pop()
        component_left = {seed}
        component_right: set[int] = set()
        queue = [seed]
        while queue:
            left = queue.pop()
            for right in left_to_right[left]:
                if right in component_right:
                    continue
                component_right.add(right)
                for connected_left in right_to_left[right]:
                    if connected_left not in component_left:
                        component_left.add(connected_left)
                        unvisited_left.discard(connected_left)
                        queue.append(connected_left)

        left_nodes = sorted(component_left)
        right_nodes = sorted(component_right)
        left_row = {value: index for index, value in enumerate(left_nodes)}
        right_col = {value: index for index, value in enumerate(right_nodes)}
        component_mask = eligible["left_index"].isin(left_nodes) & eligible["right_index"].isin(
            right_nodes
        )
        component = eligible.loc[component_mask]

        cost = np.full((len(left_nodes), len(right_nodes) + len(left_nodes)), np.inf)
        pair_to_row: dict[tuple[int, int], int] = {}
        for row_index, row in component.iterrows():
            left = int(row["left_index"])
            right = int(row["right_index"])
            score = float(row[score_col])
            clipped_score = np.clip(score, np.finfo(float).eps, 1.0 - np.finfo(float).eps)
            score_log_odds = np.log(clipped_score) - np.log1p(-clipped_score)
            threshold_log_odds = np.log(min_score) - np.log1p(-min_score)
            utility = score_log_odds - threshold_log_odds
            cost[left_row[left], right_col[right]] = -utility
            pair_to_row[(left, right)] = int(row_index)

        unmatched_cost = 1e-12
        for index in range(len(left_nodes)):
            cost[index, len(right_nodes) + index] = unmatched_cost

        assigned_rows, assigned_cols = linear_sum_assignment(cost)
        for row, col in zip(assigned_rows, assigned_cols, strict=True):
            if col < len(right_nodes) and np.isfinite(cost[row, col]):
                selected_rows.append(pair_to_row[(left_nodes[row], right_nodes[col])])

    return (
        eligible.loc[selected_rows]
        .sort_values(["left_index", "right_index"])
        .reset_index(drop=True)
    )


def _assemble_matches(
    selected: pd.DataFrame,
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_prefix: str,
    right_prefix: str,
) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    left_rows = left_df.iloc[selected["left_index"].to_numpy(dtype=int)].reset_index(drop=True)
    right_rows = right_df.iloc[selected["right_index"].to_numpy(dtype=int)].reset_index(drop=True)
    metadata = selected.drop(columns=["left_index", "right_index"]).reset_index(drop=True)
    return pd.concat(
        [
            left_rows.add_prefix(f"{left_prefix}_"),
            right_rows.add_prefix(f"{right_prefix}_"),
            metadata,
        ],
        axis=1,
    )


def probabilistic_crossmatch(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_sigma_arcsec: float | pd.Series | np.ndarray,
    right_sigma_arcsec: float | pd.Series | np.ndarray,
    *,
    left_ra: str = "ra",
    left_dec: str = "dec",
    right_ra: str = "ra",
    right_dec: str = "dec",
    candidate_radius_arcsec: float = 5.0,
    min_posterior: float = 0.5,
    prior_odds: float | None = None,
    area_solid_angle_sr: float | None = None,
    expected_match_fraction: float = 0.7,
    left_prefix: str = "gaia",
    right_prefix: str = "wise",
) -> CrossmatchResult:
    """Score every nearby pair and select globally unique local associations."""

    if not np.isfinite(candidate_radius_arcsec) or candidate_radius_arcsec <= 0:
        raise ValueError("candidate_radius_arcsec must be finite and positive")
    if not 0.0 < min_posterior < 1.0:
        raise ValueError("min_posterior must be between zero and one")

    left_sigma = _source_values(left_sigma_arcsec, len(left_df), "left_sigma_arcsec")
    right_sigma = _source_values(right_sigma_arcsec, len(right_df), "right_sigma_arcsec")
    candidates = candidate_pairs_within_radius(
        left_df,
        right_df,
        left_ra=left_ra,
        left_dec=left_dec,
        right_ra=right_ra,
        right_dec=right_dec,
        radius_arcsec=candidate_radius_arcsec,
    )

    catalogs_are_empty = left_df.empty or right_df.empty
    if prior_odds is None and catalogs_are_empty:
        prior_odds = 0.0
    elif prior_odds is None:
        if area_solid_angle_sr is None:
            raise ValueError("area_solid_angle_sr is required when prior_odds is not supplied")
        prior_odds = catalog_prior_odds(
            len(left_df),
            len(right_df),
            area_solid_angle_sr,
            expected_match_fraction=expected_match_fraction,
        )
    if not np.isfinite(prior_odds) or prior_odds < 0:
        raise ValueError("prior_odds must be finite and non-negative")

    if candidates.empty:
        candidates["sigma_left_arcsec"] = pd.Series(dtype=float)
        candidates["sigma_right_arcsec"] = pd.Series(dtype=float)
        candidates["bayes_factor_pos"] = pd.Series(dtype=float)
        candidates["posterior_match"] = pd.Series(dtype=float)
        return CrossmatchResult(pd.DataFrame(), candidates, float(prior_odds))

    left_indices = candidates["left_index"].to_numpy(dtype=int)
    right_indices = candidates["right_index"].to_numpy(dtype=int)
    candidates["sigma_left_arcsec"] = left_sigma[left_indices]
    candidates["sigma_right_arcsec"] = right_sigma[right_indices]
    candidates["bayes_factor_pos"] = budavari_szalay_bayes_factor(
        candidates["distance_arcsec"],
        candidates["sigma_left_arcsec"],
        candidates["sigma_right_arcsec"],
    )
    candidates["posterior_match"] = posterior_from_bayes_factor(
        candidates["bayes_factor_pos"], prior_odds=prior_odds
    )
    selected = resolve_unique_matches(
        candidates,
        score_col="posterior_match",
        min_score=min_posterior,
    )
    matches = _assemble_matches(selected, left_df, right_df, left_prefix, right_prefix)
    return CrossmatchResult(matches, candidates, float(prior_odds))
