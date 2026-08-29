from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

from astrobridge.astrometry import candidate_pairs_within_radius

PROTOCOL_SPLIT_PREFIX = "astrobridge-xmm-cosmos-v1|"
CALIBRATION_EPSILON = 1e-12


@dataclass(frozen=True)
class ReferenceBundle:
    """Reference cases and linked truth pairs for the XMM-COSMOS benchmark."""

    cases: pd.DataFrame
    truth_pairs: pd.DataFrame
    label_links: pd.DataFrame


class XmmCosmosBenchmarkError(ValueError):
    """Raised when the XMM-COSMOS benchmark cannot be built as specified."""


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise XmmCosmosBenchmarkError(f"{name} missing columns: {sorted(missing)}")


def _integer_id(value: object, name: str) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise XmmCosmosBenchmarkError(f"{name} must contain integer identifiers") from exc
    if not np.isfinite(numeric) or not numeric.is_integer():
        raise XmmCosmosBenchmarkError(f"{name} must contain integer identifiers")
    return str(int(numeric))


def _integer_ids(values: pd.Series, name: str) -> pd.Series:
    return values.map(lambda value: _integer_id(value, name))


def build_reference_bundle(
    xmm: pd.DataFrame,
    irac: pd.DataFrame,
    chandra: pd.DataFrame,
    *,
    label_radius_arcsec: float = 0.5,
) -> ReferenceBundle:
    """Construct independent Chandra-anchored IRAC labels without model scores."""

    if not np.isfinite(label_radius_arcsec) or label_radius_arcsec <= 0:
        raise XmmCosmosBenchmarkError("label_radius_arcsec must be finite and positive")
    _require_columns(xmm, {"ID", "RA", "DEC", "pos_err"}, "xmm")
    _require_columns(irac, {"ID", "RA", "DEC"}, "irac")
    _require_columns(
        chandra,
        {"id_xmm", "final_id_flag", "ra_irac", "dec_irac"},
        "chandra",
    )

    xmm_ids = _integer_ids(xmm["ID"], "xmm.ID")
    irac_ids = _integer_ids(irac["ID"], "irac.ID")
    if xmm_ids.duplicated().any():
        raise XmmCosmosBenchmarkError("xmm.ID must be unique")
    if irac_ids.duplicated().any():
        raise XmmCosmosBenchmarkError("irac.ID must be unique")

    chandra_work = chandra.reset_index(drop=True).copy()
    numeric_xmm = pd.to_numeric(chandra_work["id_xmm"], errors="coerce")
    mapped_mask = np.isfinite(numeric_xmm) & (numeric_xmm > 0) & (numeric_xmm % 1 == 0)
    chandra_work["_xmm_id"] = pd.Series(pd.NA, index=chandra_work.index, dtype="string")
    chandra_work.loc[mapped_mask, "_xmm_id"] = numeric_xmm.loc[mapped_mask].map(
        lambda value: str(int(value))
    )

    ra_irac = pd.to_numeric(chandra_work["ra_irac"], errors="coerce")
    dec_irac = pd.to_numeric(chandra_work["dec_irac"], errors="coerce")
    coordinate_mask = (
        mapped_mask
        & np.isfinite(ra_irac)
        & np.isfinite(dec_irac)
        & (ra_irac >= 0.0)
        & (ra_irac < 360.0)
        & (dec_irac >= -90.0)
        & (dec_irac <= 90.0)
    )
    linkable = chandra_work.loc[coordinate_mask, ["ra_irac", "dec_irac"]].copy()
    linkable["chandra_index"] = linkable.index.astype(int)
    linkable = linkable.reset_index(drop=True)
    irac_positions = pd.DataFrame(
        {
            "ra": pd.to_numeric(irac["RA"], errors="coerce"),
            "dec": pd.to_numeric(irac["DEC"], errors="coerce"),
        }
    )
    links = candidate_pairs_within_radius(
        linkable,
        irac_positions,
        left_ra="ra_irac",
        left_dec="dec_irac",
        right_ra="ra",
        right_dec="dec",
        radius_arcsec=label_radius_arcsec,
    )
    if links.empty:
        label_links = pd.DataFrame(columns=["chandra_index", "right_id", "label_distance_arcsec"])
    else:
        label_links = pd.DataFrame(
            {
                "chandra_index": linkable.iloc[links["left_index"].to_numpy(dtype=int)][
                    "chandra_index"
                ].to_numpy(dtype=int),
                "right_id": irac_ids.iloc[links["right_index"].to_numpy(dtype=int)].to_numpy(
                    dtype=str
                ),
                "label_distance_arcsec": links["distance_arcsec"].to_numpy(dtype=float),
            }
        ).sort_values(["chandra_index", "label_distance_arcsec", "right_id"], ignore_index=True)

    linked_rights = {
        int(chandra_index): list(dict.fromkeys(group["right_id"].tolist()))
        for chandra_index, group in label_links.groupby("chandra_index", sort=False)
    }
    chandra_by_xmm = {
        str(xmm_id): group
        for xmm_id, group in chandra_work.loc[mapped_mask].groupby("_xmm_id", sort=False)
    }

    case_rows: list[dict[str, object]] = []
    truth_rows: list[dict[str, str]] = []
    for xmm_id in xmm_ids:
        rows = chandra_by_xmm.get(xmm_id)
        state = "unknown"
        reason = "no_chandra_xmm_mapping"
        case_truth: list[tuple[str, str]] = []
        if rows is not None and len(rows) > 1:
            state = "ambiguous"
            reason = "multiple_chandra_sources"
            for index, row in rows.iterrows():
                flag = int(row["final_id_flag"])
                if flag in {1, 10}:
                    case_truth.extend(
                        (right_id, "acceptable") for right_id in linked_rights.get(int(index), [])
                    )
        elif rows is not None:
            index = int(rows.index[0])
            row = rows.iloc[0]
            flag = int(row["final_id_flag"])
            right_ids = linked_rights.get(index, [])
            if flag == 1 and len(right_ids) == 1:
                state = "matched"
                reason = "secure_unique_chandra_irac_link"
                case_truth.append((right_ids[0], "unique_true"))
            elif flag == 10:
                state = "ambiguous"
                reason = "chandra_identification_ambiguous"
                case_truth.extend((right_id, "acceptable") for right_id in right_ids)
            elif flag == 1 and len(right_ids) > 1:
                state = "ambiguous"
                reason = "multiple_irac_sources_within_label_radius"
                case_truth.extend((right_id, "acceptable") for right_id in right_ids)
            elif flag == 1:
                reason = "secure_chandra_reference_missing_from_irac_catalog"
            elif flag == 100:
                reason = "chandra_identification_subthreshold"
            elif flag == -99:
                reason = "chandra_identification_unidentified"
            else:
                reason = f"unsupported_chandra_identification_flag_{flag}"

        truth_complete = state == "matched"
        case_rows.append(
            {
                "case_id": xmm_id,
                "left_id": xmm_id,
                "truth_state": state,
                "truth_complete": truth_complete,
                "reference_truth_complete": truth_complete,
                "label_reason": reason,
            }
        )
        seen_truth: set[str] = set()
        for right_id, relation in case_truth:
            if right_id in seen_truth:
                continue
            seen_truth.add(right_id)
            truth_rows.append({"case_id": xmm_id, "right_id": right_id, "relation": relation})

    cases = pd.DataFrame(case_rows)
    truth_pairs = pd.DataFrame(
        truth_rows,
        columns=["case_id", "right_id", "relation"],
    )
    strict_truth = truth_pairs.loc[truth_pairs["relation"].eq("unique_true")]
    if strict_truth["right_id"].duplicated().any():
        duplicated = sorted(
            strict_truth.loc[strict_truth["right_id"].duplicated(False), "right_id"].unique()
        )
        raise XmmCosmosBenchmarkError(f"strict Chandra references reuse IRAC IDs: {duplicated[:5]}")
    return ReferenceBundle(cases=cases, truth_pairs=truth_pairs, label_links=label_links)


def _component_hash(left_ids: Iterable[str]) -> str:
    payload = ",".join(sorted(str(value) for value in left_ids))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"component-{digest}"


def assign_bipartite_components(
    candidates: pd.DataFrame,
    *,
    left_col: str = "case_id",
    right_col: str = "right_id",
) -> pd.Series:
    """Assign deterministic IDs to connected components of a bipartite candidate graph."""

    _require_columns(candidates, {left_col, right_col}, "candidates")
    if candidates.empty:
        return pd.Series(index=candidates.index, dtype="string", name="component_id")
    if candidates[left_col].isna().any() or candidates[right_col].isna().any():
        raise XmmCosmosBenchmarkError("candidate component identifiers cannot be missing")

    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(node: tuple[str, str]) -> tuple[str, str]:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(first: tuple[str, str], second: tuple[str, str]) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            if first_root > second_root:
                first_root, second_root = second_root, first_root
            parent[second_root] = first_root

    for row in candidates[[left_col, right_col]].itertuples(index=False, name=None):
        union(("left", str(row[0])), ("right", str(row[1])))

    left_members: dict[tuple[str, str], set[str]] = {}
    for node in list(parent):
        root = find(node)
        if node[0] == "left":
            left_members.setdefault(root, set()).add(node[1])
    root_ids = {root: _component_hash(members) for root, members in left_members.items()}
    values = [root_ids[find(("left", str(value)))] for value in candidates[left_col]]
    return pd.Series(values, index=candidates.index, dtype="string", name="component_id")


def component_split(left_ids: Iterable[str]) -> str:
    """Apply the frozen SHA-256 calibration/test split to one closed component."""

    payload = PROTOCOL_SPLIT_PREFIX + ",".join(sorted(str(value) for value in left_ids))
    bucket = int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big") % 10
    return "calibration" if bucket <= 2 else "test"


def apply_component_closure(
    cases: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exclude mixed-truth components and attach the frozen component-level split."""

    _require_columns(
        cases,
        {"case_id", "truth_state", "truth_complete", "reference_truth_complete"},
        "cases",
    )
    _require_columns(candidates, {"case_id", "right_id"}, "candidates")
    cases_out = cases.copy()
    candidates_out = candidates.copy()
    candidates_out["component_id"] = assign_bipartite_components(candidates_out)

    case_component_count = candidates_out.groupby("case_id")["component_id"].nunique()
    if (case_component_count > 1).any():
        raise XmmCosmosBenchmarkError("a case cannot belong to multiple candidate components")
    case_component = (
        candidates_out[["case_id", "component_id"]]
        .drop_duplicates("case_id")
        .set_index("case_id")["component_id"]
        .to_dict()
    )
    cases_out["component_id"] = cases_out["case_id"].map(case_component).astype("string")
    no_candidates = cases_out["component_id"].isna()
    isolated_components = cases_out.loc[no_candidates, "case_id"].map(
        lambda case_id: _component_hash([str(case_id)])
    )
    cases_out.loc[no_candidates, "component_id"] = isolated_components.astype("string")

    case_lookup = cases_out.set_index("case_id")
    component_cases = {
        str(component_id): sorted(set(group["case_id"]))
        for component_id, group in candidates_out.groupby("component_id", sort=False)
    }
    for row in cases_out.loc[no_candidates].itertuples(index=False):
        component_cases[str(row.component_id)] = [str(row.case_id)]

    component_status: dict[str, str] = {}
    for component_id, member_ids in component_cases.items():
        members = case_lookup.loc[member_ids]
        strict = members["reference_truth_complete"].astype(bool) & members["truth_state"].isin(
            ["matched", "unmatched"]
        )
        if strict.all():
            component_status[component_id] = component_split(member_ids)
        elif strict.any():
            component_status[component_id] = "excluded"
        else:
            component_status[component_id] = "descriptive"

    cases_out["split"] = cases_out["component_id"].map(component_status).astype("string")
    cases_out["closure_excluded"] = cases_out["reference_truth_complete"].astype(bool) & cases_out[
        "split"
    ].eq("excluded")
    cases_out["truth_complete"] = cases_out["reference_truth_complete"].astype(bool) & cases_out[
        "split"
    ].isin(["calibration", "test"])
    component_split_map = {
        component_id: split
        for component_id, split in component_status.items()
        if component_id in set(candidates_out["component_id"])
    }
    candidates_out["split"] = (
        candidates_out["component_id"].map(component_split_map).astype("string")
    )
    return cases_out, candidates_out


def apply_logit_intercept(
    probabilities: pd.Series | np.ndarray,
    intercept: float,
) -> np.ndarray:
    """Apply the frozen intercept-only recalibration to binary pair probabilities."""

    values = np.asarray(probabilities, dtype=float)
    if np.any(~np.isfinite(values)) or np.any((values < 0.0) | (values > 1.0)):
        raise XmmCosmosBenchmarkError("probabilities must be finite and in [0, 1]")
    if not np.isfinite(intercept):
        raise XmmCosmosBenchmarkError("intercept must be finite")
    clipped = np.clip(values, CALIBRATION_EPSILON, 1.0 - CALIBRATION_EPSILON)
    logits = np.log(clipped) - np.log1p(-clipped)
    return expit(logits + float(intercept))


def fit_logit_intercept(
    probabilities: pd.Series | np.ndarray,
    labels: pd.Series | np.ndarray,
) -> float:
    """Fit one additive logit intercept by unweighted binary maximum likelihood."""

    values = np.asarray(probabilities, dtype=float)
    targets = np.asarray(labels, dtype=float)
    if values.shape != targets.shape or values.ndim != 1:
        raise XmmCosmosBenchmarkError("probabilities and labels must be equal-length vectors")
    if values.size == 0:
        raise XmmCosmosBenchmarkError("calibration requires candidate pairs")
    if np.any(~np.isfinite(targets)) or np.any(~np.isin(targets, [0.0, 1.0])):
        raise XmmCosmosBenchmarkError("calibration labels must be binary")
    if targets.min() == targets.max():
        raise XmmCosmosBenchmarkError("calibration requires positive and negative pairs")

    def score(intercept: float) -> float:
        return float((apply_logit_intercept(values, intercept) - targets).sum())

    return float(brentq(score, -60.0, 60.0, xtol=1e-12, rtol=1e-12))


def wilson_interval(
    successes: int, total: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if total <= 0:
        raise XmmCosmosBenchmarkError("Wilson interval requires a positive total")
    if successes < 0 or successes > total:
        raise XmmCosmosBenchmarkError("successes must be between zero and total")
    if not np.isfinite(z) or z <= 0:
        raise XmmCosmosBenchmarkError("z must be finite and positive")
    proportion = successes / total
    denominator = 1.0 + z**2 / total
    center = (proportion + z**2 / (2.0 * total)) / denominator
    half_width = (
        z * np.sqrt(proportion * (1.0 - proportion) / total + z**2 / (4.0 * total**2)) / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def cluster_bootstrap_ratios(
    component_counts: pd.DataFrame,
    ratio_columns: dict[str, tuple[str, str]],
    *,
    replicates: int = 10_000,
    seed: int = 20_260_828,
) -> dict[str, dict[str, float | int | None]]:
    """Bootstrap ratios by resampling complete component count vectors."""

    required = {column for pair in ratio_columns.values() for column in pair}
    _require_columns(component_counts, required, "component_counts")
    if component_counts.empty:
        raise XmmCosmosBenchmarkError("component bootstrap requires at least one component")
    if replicates <= 0:
        raise XmmCosmosBenchmarkError("replicates must be positive")
    values = component_counts[list(required)].apply(pd.to_numeric, errors="raise")
    if np.any(~np.isfinite(values.to_numpy(dtype=float))) or np.any(
        values.to_numpy(dtype=float) < 0
    ):
        raise XmmCosmosBenchmarkError("component counts must be finite and non-negative")

    rng = np.random.default_rng(seed)
    count = len(component_counts)
    draws: dict[str, list[float]] = {name: [] for name in ratio_columns}
    columns = list(values.columns)
    array = values.to_numpy(dtype=float)
    column_index = {column: index for index, column in enumerate(columns)}
    for _ in range(replicates):
        sampled = array[rng.integers(0, count, size=count)].sum(axis=0)
        for name, (numerator_col, denominator_col) in ratio_columns.items():
            denominator = sampled[column_index[denominator_col]]
            if denominator > 0:
                draws[name].append(sampled[column_index[numerator_col]] / denominator)

    output: dict[str, dict[str, float | int | None]] = {}
    for name, metric_draws in draws.items():
        if len(metric_draws) < 0.9 * replicates:
            output[name] = {
                "lower_95": None,
                "upper_95": None,
                "valid_replicates": len(metric_draws),
                "reason": "metric_defined_in_fewer_than_90_percent_of_replicates",
            }
        else:
            lower, upper = np.percentile(metric_draws, [2.5, 97.5])
            output[name] = {
                "lower_95": float(lower),
                "upper_95": float(upper),
                "valid_replicates": len(metric_draws),
                "reason": None,
            }
    return output
