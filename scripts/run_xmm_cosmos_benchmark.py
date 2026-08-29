from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table

from astrobridge.bayes import catalog_prior_odds
from astrobridge.external_benchmark import evaluate_external_benchmark
from astrobridge.matching import probabilistic_crossmatch, resolve_unique_matches
from astrobridge.xmm_cosmos import (
    apply_component_closure,
    apply_logit_intercept,
    build_reference_bundle,
    cluster_bootstrap_ratios,
    fit_logit_intercept,
    wilson_interval,
)

PROTOCOL_BOUNDARY = "dcf57d9c9bda375630566422de2b735af3c0166d"
NWAY_COMMIT = "a37be1f9402ea2e7d6ff5f022f5f23ad94ff15fc"
CANDIDATE_RADIUS_ARCSEC = 20.0
IRAC_SIGMA_ARCSEC = 0.5
LABEL_RADIUS_ARCSEC = 0.5
EXPECTED_MATCH_FRACTION = 0.9
MIN_POSTERIOR = 0.5
SKY_AREA_SQUARE_DEG = 2.0
CONTROL_SHIFT_ARCSEC = 60.0
CONTROL_VETO_ARCSEC = 20.0
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20_260_828


@dataclass(frozen=True)
class InputSpec:
    filename: str
    url: str
    sha256: str
    expected_bytes: int
    expected_rows: int


INPUTS = (
    InputSpec(
        filename="COSMOS_XMM.fits",
        url=(
            "https://raw.githubusercontent.com/JohannesBuchner/nway/"
            f"{NWAY_COMMIT}/doc/COSMOS_XMM.fits"
        ),
        sha256="9b2728376ff1b3f265923a2b7d2cd5a1f94da67739ef8eee308078017ac1a970",
        expected_bytes=51_840,
        expected_rows=1_797,
    ),
    InputSpec(
        filename="COSMOS_IRAC.fits",
        url=(
            "https://raw.githubusercontent.com/JohannesBuchner/nway/"
            f"{NWAY_COMMIT}/doc/COSMOS_IRAC.fits"
        ),
        sha256="7db44b04fe8fcffc87087f8586e31c766128e4343d86a9fb2aca85e1ed9ec274",
        expected_bytes=11_067_840,
        expected_rows=345_512,
    ),
    InputSpec(
        filename="chandra_COSMOS_legacy_opt_NIR_counterparts_20160113_4d.fits",
        url=(
            "https://irsa.ipac.caltech.edu/data/COSMOS/tables/chandra/"
            "chandra_COSMOS_legacy_opt_NIR_counterparts_20160113_4d.fits"
        ),
        sha256="3a9eab9fc7244d444b0500ebcdfa4b20aeda520dd29114ea5a1b9d1b1e16c5f2",
        expected_bytes=1_252_800,
        expected_rows=4_016,
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_and_verify(spec: InputSpec, raw_dir: Path) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / spec.filename
    if not path.exists():
        request = urllib.request.Request(
            spec.url,
            headers={"User-Agent": "AstroBridge-XMM-COSMOS-benchmark/1"},
        )
        temporary = path.with_suffix(path.suffix + ".part")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                with temporary.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()

    actual_hash = _sha256(path)
    actual_bytes = path.stat().st_size
    if actual_hash != spec.sha256:
        raise RuntimeError(f"checksum mismatch for {spec.filename}: {actual_hash} != {spec.sha256}")
    if actual_bytes != spec.expected_bytes:
        raise RuntimeError(
            f"byte-count mismatch for {spec.filename}: {actual_bytes} != {spec.expected_bytes}"
        )
    with fits.open(path, memmap=True) as hdus:
        actual_rows = len(hdus[1].data)
        columns = list(hdus[1].columns.names)
        sky_area = hdus[1].header.get("SKYAREA")
    if actual_rows != spec.expected_rows:
        raise RuntimeError(
            f"row-count mismatch for {spec.filename}: {actual_rows} != {spec.expected_rows}"
        )
    return {
        **asdict(spec),
        "path": str(path.resolve()),
        "actual_sha256": actual_hash,
        "actual_bytes": actual_bytes,
        "actual_rows": actual_rows,
        "columns": columns,
        "skyarea_square_deg": sky_area,
        "file_mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
    }


def _load_table(path: Path) -> pd.DataFrame:
    return Table.read(path, hdu=1).to_pandas()


def _git_output(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], text=True, encoding="utf-8").strip()


def _assert_clean_tracked_worktree() -> str:
    dirty = _git_output("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise RuntimeError("tracked worktree must be clean before the benchmark run")
    return _git_output("rev-parse", "HEAD")


def _square_degrees_to_steradians(area_square_deg: float) -> float:
    return float(area_square_deg * (np.pi / 180.0) ** 2)


def _selection_pairs(candidates: pd.DataFrame, score_col: str) -> set[tuple[int, int]]:
    selected = resolve_unique_matches(
        candidates,
        score_col=score_col,
        min_score=MIN_POSTERIOR,
    )
    return set(
        zip(
            selected["left_index"].astype(int),
            selected["right_index"].astype(int),
            strict=True,
        )
    )


def _build_scored_candidates(
    xmm: pd.DataFrame,
    irac: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    xmm_model = pd.DataFrame(
        {
            "source_id": xmm["ID"].map(lambda value: str(int(value))),
            "ra": pd.to_numeric(xmm["RA"], errors="raise"),
            "dec": pd.to_numeric(xmm["DEC"], errors="raise"),
            "position_sigma_arcsec": pd.to_numeric(xmm["pos_err"], errors="raise"),
        }
    )
    irac_model = pd.DataFrame(
        {
            "source_id": irac["ID"].map(lambda value: str(int(value))),
            "ra": pd.to_numeric(irac["RA"], errors="raise"),
            "dec": pd.to_numeric(irac["DEC"], errors="raise"),
        }
    )
    prior_odds = catalog_prior_odds(
        len(xmm_model),
        len(irac_model),
        _square_degrees_to_steradians(SKY_AREA_SQUARE_DEG),
        expected_match_fraction=EXPECTED_MATCH_FRACTION,
    )
    result = probabilistic_crossmatch(
        xmm_model,
        irac_model,
        left_sigma_arcsec=xmm_model["position_sigma_arcsec"],
        right_sigma_arcsec=IRAC_SIGMA_ARCSEC,
        candidate_radius_arcsec=CANDIDATE_RADIUS_ARCSEC,
        min_posterior=MIN_POSTERIOR,
        prior_odds=prior_odds,
        left_prefix="xmm",
        right_prefix="irac",
    )
    raw_selected = _selection_pairs(result.candidates, "posterior_match")
    left_indices = result.candidates["left_index"].to_numpy(dtype=int)
    right_indices = result.candidates["right_index"].to_numpy(dtype=int)
    candidates = result.candidates.copy()
    candidates["case_id"] = xmm_model.iloc[left_indices]["source_id"].to_numpy(dtype=str)
    candidates["left_id"] = candidates["case_id"]
    candidates["right_id"] = irac_model.iloc[right_indices]["source_id"].to_numpy(dtype=str)
    candidates["selected_raw"] = [
        (left_index, right_index) in raw_selected
        for left_index, right_index in zip(left_indices, right_indices, strict=True)
    ]
    return candidates, prior_odds


def _fit_and_apply_calibration(
    cases: pd.DataFrame,
    truth_pairs: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, float, dict[str, int]]:
    calibration_cases = set(cases.loc[cases["split"].eq("calibration"), "case_id"])
    truth_map = dict(
        truth_pairs.loc[
            truth_pairs["case_id"].isin(calibration_cases)
            & truth_pairs["relation"].eq("unique_true"),
            ["case_id", "right_id"],
        ].itertuples(index=False, name=None)
    )
    candidates_by_case = {
        case_id: set(group["right_id"])
        for case_id, group in candidates.loc[candidates["case_id"].isin(calibration_cases)].groupby(
            "case_id", sort=False
        )
    }
    present_cases = {
        case_id
        for case_id, right_id in truth_map.items()
        if right_id in candidates_by_case.get(case_id, set())
    }
    fit_rows = candidates.loc[candidates["case_id"].isin(present_cases)].copy()
    labels = np.asarray(
        [truth_map[row.case_id] == row.right_id for row in fit_rows.itertuples(index=False)],
        dtype=float,
    )
    intercept = fit_logit_intercept(fit_rows["posterior_match"], labels)
    output = candidates.copy()
    output["posterior_calibrated"] = apply_logit_intercept(output["posterior_match"], intercept)
    calibrated_selected = _selection_pairs(output, "posterior_calibrated")
    output["selected_calibrated"] = [
        (left_index, right_index) in calibrated_selected
        for left_index, right_index in zip(
            output["left_index"].astype(int),
            output["right_index"].astype(int),
            strict=True,
        )
    ]
    fit_counts = {
        "calibration_cases": len(calibration_cases),
        "cases_with_truth_candidate_present": len(present_cases),
        "candidate_pairs": len(fit_rows),
        "positive_pairs": int(labels.sum()),
        "negative_pairs": int(len(labels) - labels.sum()),
    }
    return output, intercept, fit_counts


def _evaluate_split(
    cases: pd.DataFrame,
    truth_pairs: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    split: str,
    score_col: str,
    selected_col: str,
) -> dict[str, Any]:
    split_cases = cases.loc[cases["split"].eq(split)].copy()
    case_ids = set(split_cases["case_id"])
    split_truth = truth_pairs.loc[truth_pairs["case_id"].isin(case_ids)].copy()
    split_candidates = candidates.loc[candidates["case_id"].isin(case_ids)].copy()
    split_candidates["posterior_match"] = split_candidates[score_col]
    split_candidates["selected"] = split_candidates[selected_col].astype(bool)
    evaluation = evaluate_external_benchmark(
        split_cases,
        split_truth,
        split_candidates,
    )
    return evaluation.to_dict()


def _attach_case_outcomes(
    cases: pd.DataFrame,
    truth_pairs: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    output = cases.copy()
    candidate_counts = candidates.groupby("case_id").size().to_dict()
    output["candidate_count"] = output["case_id"].map(candidate_counts).fillna(0).astype(int)
    truth_map = dict(
        truth_pairs.loc[
            truth_pairs["relation"].eq("unique_true"), ["case_id", "right_id"]
        ].itertuples(index=False, name=None)
    )
    raw_selected = dict(
        candidates.loc[candidates["selected_raw"], ["case_id", "right_id"]].itertuples(
            index=False, name=None
        )
    )
    calibrated_selected = dict(
        candidates.loc[candidates["selected_calibrated"], ["case_id", "right_id"]].itertuples(
            index=False, name=None
        )
    )
    output["truth_right_id"] = output["case_id"].map(truth_map).astype("string")
    output["selected_right_id_raw"] = output["case_id"].map(raw_selected).astype("string")
    output["selected_right_id_calibrated"] = (
        output["case_id"].map(calibrated_selected).astype("string")
    )
    truth_edges = candidates.merge(
        truth_pairs.loc[truth_pairs["relation"].eq("unique_true"), ["case_id", "right_id"]],
        on=["case_id", "right_id"],
        how="inner",
    )
    truth_distance = truth_edges.set_index("case_id")["distance_arcsec"].to_dict()
    output["truth_in_candidates"] = output["case_id"].isin(set(truth_edges["case_id"]))
    output["truth_distance_arcsec"] = output["case_id"].map(truth_distance)
    output["correct_raw"] = (
        output["selected_right_id_raw"].eq(output["truth_right_id"]).fillna(False).astype(bool)
    )
    output["correct_calibrated"] = (
        output["selected_right_id_calibrated"]
        .eq(output["truth_right_id"])
        .fillna(False)
        .astype(bool)
    )
    return output


def _reference_summary(cases: pd.DataFrame, truth_pairs: pd.DataFrame) -> dict[str, Any]:
    state_counts = cases["truth_state"].value_counts().sort_index().to_dict()
    reason_counts = cases["label_reason"].value_counts().sort_index().to_dict()
    return {
        "total_xmm_cases": len(cases),
        "truth_state_counts": {str(key): int(value) for key, value in state_counts.items()},
        "label_reason_counts": {str(key): int(value) for key, value in reason_counts.items()},
        "strict_truth_pairs": int(truth_pairs["relation"].eq("unique_true").sum()),
        "acceptable_ambiguous_pairs": int(truth_pairs["relation"].eq("acceptable").sum()),
        "closure_excluded_strict_cases": int(cases["closure_excluded"].sum()),
        "calibration_cases": int(cases["split"].eq("calibration").sum()),
        "test_cases": int(cases["split"].eq("test").sum()),
    }


def _ambiguous_summary(
    cases: pd.DataFrame,
    truth_pairs: pd.DataFrame,
    candidates: pd.DataFrame,
) -> dict[str, Any]:
    ambiguous_ids = set(cases.loc[cases["truth_state"].eq("ambiguous"), "case_id"])
    acceptable = truth_pairs.loc[
        truth_pairs["case_id"].isin(ambiguous_ids) & truth_pairs["relation"].eq("acceptable")
    ]
    truth_sets = {
        case_id: set(group["right_id"])
        for case_id, group in acceptable.groupby("case_id", sort=False)
    }
    candidate_sets = {
        case_id: set(group["right_id"])
        for case_id, group in candidates.loc[candidates["case_id"].isin(ambiguous_ids)].groupby(
            "case_id", sort=False
        )
    }
    raw_selected_ids = set(
        candidates.loc[
            candidates["case_id"].isin(ambiguous_ids) & candidates["selected_raw"],
            "case_id",
        ]
    )
    cases_with_reference_set = len(truth_sets)
    all_present = sum(
        truth_set.issubset(candidate_sets.get(case_id, set()))
        for case_id, truth_set in truth_sets.items()
    )
    any_present = sum(
        bool(truth_set.intersection(candidate_sets.get(case_id, set())))
        for case_id, truth_set in truth_sets.items()
    )
    return {
        "ambiguous_cases": len(ambiguous_ids),
        "cases_with_reference_linked_irac_set": cases_with_reference_set,
        "all_reference_irac_candidates_present": int(all_present),
        "any_reference_irac_candidate_present": int(any_present),
        "raw_abstentions": len(ambiguous_ids - raw_selected_ids),
    }


def _build_shifted_controls(
    test_cases: pd.DataFrame,
    xmm: pd.DataFrame,
    irac: pd.DataFrame,
    chandra: pd.DataFrame,
    prior_odds: float,
    calibration_intercept: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    xmm_lookup = xmm.assign(case_id=xmm["ID"].map(lambda value: str(int(value)))).set_index(
        "case_id"
    )
    controls = test_cases[["case_id", "component_id"]].copy()
    controls["parent_case_id"] = controls.pop("case_id")
    controls["control_id"] = "shift-east-60-" + controls["parent_case_id"]
    controls["ra_original"] = controls["parent_case_id"].map(xmm_lookup["RA"])
    controls["dec_original"] = controls["parent_case_id"].map(xmm_lookup["DEC"])
    controls["position_sigma_arcsec"] = controls["parent_case_id"].map(xmm_lookup["pos_err"])
    cos_dec = np.cos(np.deg2rad(controls["dec_original"].to_numpy(dtype=float)))
    controls["ra"] = (controls["ra_original"] + CONTROL_SHIFT_ARCSEC / (3600.0 * cos_dec)) % 360.0
    controls["dec"] = controls["dec_original"]

    irac_ra = pd.to_numeric(irac["RA"], errors="coerce").to_numpy(dtype=float)
    irac_dec = pd.to_numeric(irac["DEC"], errors="coerce").to_numpy(dtype=float)
    ra_margin = CANDIDATE_RADIUS_ARCSEC / (3600.0 * cos_dec)
    dec_margin = CANDIDATE_RADIUS_ARCSEC / 3600.0
    inside_bounds = (
        (controls["ra"].to_numpy(dtype=float) >= np.nanmin(irac_ra) + ra_margin)
        & (controls["ra"].to_numpy(dtype=float) <= np.nanmax(irac_ra) - ra_margin)
        & (controls["dec"].to_numpy(dtype=float) >= np.nanmin(irac_dec) + dec_margin)
        & (controls["dec"].to_numpy(dtype=float) <= np.nanmax(irac_dec) - dec_margin)
    )

    chandra_ra = pd.to_numeric(chandra["RA_x"], errors="coerce").to_numpy(dtype=float)
    chandra_dec = pd.to_numeric(chandra["DEC_x"], errors="coerce").to_numpy(dtype=float)
    real_xray_ra = np.concatenate(
        [pd.to_numeric(xmm["RA"], errors="raise").to_numpy(dtype=float), chandra_ra]
    )
    real_xray_dec = np.concatenate(
        [pd.to_numeric(xmm["DEC"], errors="raise").to_numpy(dtype=float), chandra_dec]
    )
    finite_xray = (
        np.isfinite(real_xray_ra)
        & np.isfinite(real_xray_dec)
        & (real_xray_ra >= 0.0)
        & (real_xray_ra < 360.0)
        & (real_xray_dec >= -90.0)
        & (real_xray_dec <= 90.0)
    )
    control_coords = SkyCoord(
        controls["ra"].to_numpy(dtype=float) * u.deg,
        controls["dec"].to_numpy(dtype=float) * u.deg,
    )
    xray_coords = SkyCoord(real_xray_ra[finite_xray] * u.deg, real_xray_dec[finite_xray] * u.deg)
    _, nearest_xray, _ = control_coords.match_to_catalog_sky(xray_coords)
    clear_of_xray = nearest_xray.arcsec > CONTROL_VETO_ARCSEC

    controls["rejection_reason"] = ""
    controls.loc[~inside_bounds, "rejection_reason"] = "candidate_circle_crosses_irac_bounds"
    controls.loc[inside_bounds & ~clear_of_xray, "rejection_reason"] = (
        "within_20_arcsec_of_cataloged_xray_source"
    )
    controls["retained"] = inside_bounds & clear_of_xray
    controls["nearest_cataloged_xray_arcsec"] = nearest_xray.arcsec
    retained = controls.loc[controls["retained"]].reset_index(drop=True)

    irac_model = pd.DataFrame(
        {
            "source_id": irac["ID"].map(lambda value: str(int(value))),
            "ra": pd.to_numeric(irac["RA"], errors="raise"),
            "dec": pd.to_numeric(irac["DEC"], errors="raise"),
        }
    )
    result = probabilistic_crossmatch(
        retained[["control_id", "ra", "dec", "position_sigma_arcsec"]],
        irac_model,
        left_sigma_arcsec=retained["position_sigma_arcsec"],
        right_sigma_arcsec=IRAC_SIGMA_ARCSEC,
        candidate_radius_arcsec=CANDIDATE_RADIUS_ARCSEC,
        min_posterior=MIN_POSTERIOR,
        prior_odds=prior_odds,
        left_prefix="control",
        right_prefix="irac",
    )
    raw_selected = _selection_pairs(result.candidates, "posterior_match")
    control_candidates = result.candidates.copy()
    control_candidates["posterior_calibrated"] = apply_logit_intercept(
        control_candidates["posterior_match"], calibration_intercept
    )
    calibrated_selected = _selection_pairs(control_candidates, "posterior_calibrated")
    left_indices = control_candidates["left_index"].to_numpy(dtype=int)
    right_indices = control_candidates["right_index"].to_numpy(dtype=int)
    control_candidates["control_id"] = retained.iloc[left_indices]["control_id"].to_numpy(dtype=str)
    control_candidates["parent_case_id"] = retained.iloc[left_indices]["parent_case_id"].to_numpy(
        dtype=str
    )
    control_candidates["component_id"] = retained.iloc[left_indices]["component_id"].to_numpy(
        dtype=str
    )
    control_candidates["right_id"] = irac_model.iloc[right_indices]["source_id"].to_numpy(dtype=str)
    control_candidates["selected_raw"] = [
        (left_index, right_index) in raw_selected
        for left_index, right_index in zip(left_indices, right_indices, strict=True)
    ]
    control_candidates["selected_calibrated"] = [
        (left_index, right_index) in calibrated_selected
        for left_index, right_index in zip(left_indices, right_indices, strict=True)
    ]
    raw_selected_controls = set(
        control_candidates.loc[control_candidates["selected_raw"], "control_id"]
    )
    calibrated_selected_controls = set(
        control_candidates.loc[control_candidates["selected_calibrated"], "control_id"]
    )
    controls["selected_raw"] = controls["control_id"].isin(raw_selected_controls)
    controls["selected_calibrated"] = controls["control_id"].isin(calibrated_selected_controls)
    candidate_count = control_candidates.groupby("control_id").size().to_dict()
    controls["candidate_count"] = controls["control_id"].map(candidate_count).fillna(0).astype(int)
    return controls, control_candidates


def _proportion_summary(successes: int, total: int) -> dict[str, Any]:
    if total == 0:
        return {
            "successes": successes,
            "total": total,
            "rate": None,
            "wilson_95": None,
        }
    lower, upper = wilson_interval(successes, total)
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total,
        "wilson_95": {"lower": lower, "upper": upper},
    }


def _uncertainty_and_gates(
    test_cases: pd.DataFrame,
    controls: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Any]]:
    retained_controls = controls.loc[controls["retained"]]
    case_counts = test_cases[
        [
            "component_id",
            "truth_in_candidates",
            "correct_raw",
            "selected_right_id_raw",
            "correct_calibrated",
            "selected_right_id_calibrated",
        ]
    ].copy()
    case_counts["truth_total"] = 1
    case_counts["truth_present"] = case_counts["truth_in_candidates"].astype(int)
    case_counts["tp_raw"] = case_counts["correct_raw"].astype(int)
    case_counts["selected_raw_count"] = case_counts["selected_right_id_raw"].notna().astype(int)
    case_counts["tp_calibrated"] = case_counts["correct_calibrated"].astype(int)
    case_counts["selected_calibrated_count"] = (
        case_counts["selected_right_id_calibrated"].notna().astype(int)
    )
    component_counts = case_counts.groupby("component_id", as_index=False).agg(
        truth_total=("truth_total", "sum"),
        truth_present=("truth_present", "sum"),
        tp_raw=("tp_raw", "sum"),
        selected_raw_count=("selected_raw_count", "sum"),
        tp_calibrated=("tp_calibrated", "sum"),
        selected_calibrated_count=("selected_calibrated_count", "sum"),
    )
    control_counts = retained_controls.groupby("component_id", as_index=False).agg(
        control_total=("retained", "sum"),
        control_selected_raw=("selected_raw", "sum"),
        control_selected_calibrated=("selected_calibrated", "sum"),
    )
    component_counts = component_counts.merge(control_counts, on="component_id", how="left")
    for column in ["control_total", "control_selected_raw", "control_selected_calibrated"]:
        component_counts[column] = component_counts[column].fillna(0).astype(int)

    ratios = {
        "candidate_coverage": ("truth_present", "truth_total"),
        "precision_raw": ("tp_raw", "selected_raw_count"),
        "recall_raw": ("tp_raw", "truth_total"),
        "control_selection_rate_raw": ("control_selected_raw", "control_total"),
        "precision_calibrated": ("tp_calibrated", "selected_calibrated_count"),
        "recall_calibrated": ("tp_calibrated", "truth_total"),
        "control_selection_rate_calibrated": (
            "control_selected_calibrated",
            "control_total",
        ),
    }
    bootstrap = cluster_bootstrap_ratios(
        component_counts,
        ratios,
        replicates=BOOTSTRAP_REPLICATES,
        seed=BOOTSTRAP_SEED,
    )
    exact = {
        "candidate_coverage": _proportion_summary(
            int(case_counts["truth_present"].sum()), len(case_counts)
        ),
        "precision_raw": _proportion_summary(
            int(case_counts["tp_raw"].sum()), int(case_counts["selected_raw_count"].sum())
        ),
        "recall_raw": _proportion_summary(int(case_counts["tp_raw"].sum()), len(case_counts)),
        "control_selection_rate_raw": _proportion_summary(
            int(retained_controls["selected_raw"].sum()), len(retained_controls)
        ),
        "precision_calibrated": _proportion_summary(
            int(case_counts["tp_calibrated"].sum()),
            int(case_counts["selected_calibrated_count"].sum()),
        ),
        "recall_calibrated": _proportion_summary(
            int(case_counts["tp_calibrated"].sum()), len(case_counts)
        ),
        "control_selection_rate_calibrated": _proportion_summary(
            int(retained_controls["selected_calibrated"].sum()), len(retained_controls)
        ),
    }
    uncertainty = {
        "bootstrap_unit": "closed_bipartite_component",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "component_count": len(component_counts),
        "exact_and_wilson": exact,
        "component_bootstrap_percentile_95": bootstrap,
    }

    coverage = exact["candidate_coverage"]
    precision = exact["precision_raw"]
    recall = exact["recall_raw"]
    control = exact["control_selection_rate_raw"]
    gate_checks = {
        "coverage_point_at_least_0_98": coverage["rate"] >= 0.98,
        "coverage_bootstrap_lower_at_least_0_95": bootstrap["candidate_coverage"]["lower_95"]
        >= 0.95,
        "precision_point_at_least_0_95": precision["rate"] >= 0.95,
        "precision_bootstrap_lower_at_least_0_90": bootstrap["precision_raw"]["lower_95"] >= 0.90,
        "recall_point_at_least_0_95": recall["rate"] >= 0.95,
        "recall_bootstrap_lower_at_least_0_90": bootstrap["recall_raw"]["lower_95"] >= 0.90,
        "control_point_at_most_0_05": control["rate"] <= 0.05,
        "control_bootstrap_upper_at_most_0_10": bootstrap["control_selection_rate_raw"]["upper_95"]
        <= 0.10,
    }
    gates = {
        "checks": gate_checks,
        "passed": all(gate_checks.values()),
        "scope": "limited single-field engineering benchmark only",
    }
    return uncertainty, gates


def _quartile_strata(test_cases: pd.DataFrame, calibration_cases: pd.DataFrame) -> dict[str, Any]:
    variables = ["xmm_position_sigma_arcsec", "candidate_count", "truth_distance_arcsec"]
    output: dict[str, Any] = {}
    for variable in variables:
        calibration_values = pd.to_numeric(calibration_cases[variable], errors="coerce")
        calibration_values = calibration_values[np.isfinite(calibration_values)]
        boundaries = np.quantile(calibration_values, [0.25, 0.5, 0.75]).tolist()
        test_values = pd.to_numeric(test_cases[variable], errors="coerce").to_numpy(dtype=float)
        bins = np.searchsorted(np.asarray(boundaries), test_values, side="right")
        rows: list[dict[str, Any]] = []
        for index in range(4):
            mask = bins == index
            denominator = int(mask.sum())
            rows.append(
                {
                    "quartile_index": index + 1,
                    "cases": denominator,
                    "candidate_coverage": (
                        float(test_cases.loc[mask, "truth_in_candidates"].mean())
                        if denominator
                        else None
                    ),
                    "raw_recall": (
                        float(test_cases.loc[mask, "correct_raw"].mean()) if denominator else None
                    ),
                    "calibrated_recall": (
                        float(test_cases.loc[mask, "correct_calibrated"].mean())
                        if denominator
                        else None
                    ),
                }
            )
        output[variable] = {
            "calibration_quartile_boundaries": boundaries,
            "test_results": rows,
        }
    return output


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.bool_, np.integer)):
        return value.item()
    if isinstance(value, np.floating):
        return None if not np.isfinite(value) else value.item()
    if pd.isna(value):
        return None
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def run(raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    git_commit = _assert_clean_tracked_worktree()
    started_utc = datetime.now(UTC)
    input_manifest = [_download_and_verify(spec, raw_dir) for spec in INPUTS]
    paths = {item["filename"]: Path(item["path"]) for item in input_manifest}
    xmm = _load_table(paths["COSMOS_XMM.fits"])
    irac = _load_table(paths["COSMOS_IRAC.fits"])
    chandra = _load_table(paths["chandra_COSMOS_legacy_opt_NIR_counterparts_20160113_4d.fits"])

    reference = build_reference_bundle(
        xmm,
        irac,
        chandra,
        label_radius_arcsec=LABEL_RADIUS_ARCSEC,
    )
    candidates, prior_odds = _build_scored_candidates(xmm, irac)
    cases, candidates = apply_component_closure(reference.cases, candidates)
    candidates, calibration_intercept, calibration_fit = _fit_and_apply_calibration(
        cases,
        reference.truth_pairs,
        candidates,
    )
    cases = _attach_case_outcomes(cases, reference.truth_pairs, candidates)
    xmm_features = xmm.assign(case_id=xmm["ID"].map(lambda value: str(int(value))))[
        ["case_id", "RA", "DEC", "pos_err"]
    ].rename(
        columns={
            "RA": "xmm_ra_deg",
            "DEC": "xmm_dec_deg",
            "pos_err": "xmm_position_sigma_arcsec",
        }
    )
    cases = cases.merge(xmm_features, on="case_id", how="left", validate="one_to_one")

    raw_calibration = _evaluate_split(
        cases,
        reference.truth_pairs,
        candidates,
        split="calibration",
        score_col="posterior_match",
        selected_col="selected_raw",
    )
    raw_test = _evaluate_split(
        cases,
        reference.truth_pairs,
        candidates,
        split="test",
        score_col="posterior_match",
        selected_col="selected_raw",
    )
    calibrated_test = _evaluate_split(
        cases,
        reference.truth_pairs,
        candidates,
        split="test",
        score_col="posterior_calibrated",
        selected_col="selected_calibrated",
    )

    test_cases = cases.loc[cases["split"].eq("test")].copy()
    calibration_cases = cases.loc[cases["split"].eq("calibration")].copy()
    controls, control_candidates = _build_shifted_controls(
        test_cases,
        xmm,
        irac,
        chandra,
        prior_odds,
        calibration_intercept,
    )
    uncertainty, gates = _uncertainty_and_gates(test_cases, controls)

    metrics = {
        "benchmark_id": "xmm-cosmos-irac-chandra-v1",
        "protocol_boundary": PROTOCOL_BOUNDARY,
        "run_commit": git_commit,
        "configuration": {
            "candidate_radius_arcsec": CANDIDATE_RADIUS_ARCSEC,
            "irac_sigma_arcsec": IRAC_SIGMA_ARCSEC,
            "label_radius_arcsec": LABEL_RADIUS_ARCSEC,
            "expected_match_fraction": EXPECTED_MATCH_FRACTION,
            "min_posterior": MIN_POSTERIOR,
            "sky_area_square_deg": SKY_AREA_SQUARE_DEG,
            "prior_odds": prior_odds,
            "control_shift_arcsec": CONTROL_SHIFT_ARCSEC,
            "control_veto_arcsec": CONTROL_VETO_ARCSEC,
        },
        "reference": _reference_summary(cases, reference.truth_pairs),
        "calibration_fit": {
            **calibration_fit,
            "logit_intercept": calibration_intercept,
        },
        "raw_calibration": raw_calibration,
        "raw_test_primary": raw_test,
        "calibrated_test_secondary": calibrated_test,
        "ambiguous_descriptive": _ambiguous_summary(cases, reference.truth_pairs, candidates),
        "shifted_controls": {
            "constructed": len(controls),
            "retained": int(controls["retained"].sum()),
            "rejected": int((~controls["retained"]).sum()),
            "selected_raw": int(controls["selected_raw"].sum()),
            "selected_calibrated": int(controls["selected_calibrated"].sum()),
            "interpretation": "pseudo-negative positional stress controls, not ground truth",
        },
        "quartile_strata": _quartile_strata(test_cases, calibration_cases),
        "uncertainty": uncertainty,
        "decision_rule": gates,
        "scope_warning": (
            "One COSMOS field validates neither all-sky generalization nor Gaia-AllWISE "
            "epoch propagation; passing is not NASA readiness."
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    cases.sort_values("case_id").to_csv(output_dir / "cases.csv", index=False, lineterminator="\n")
    reference.truth_pairs.sort_values(["case_id", "right_id"]).to_csv(
        output_dir / "truth_pairs.csv", index=False, lineterminator="\n"
    )
    reference.label_links.sort_values(["chandra_index", "right_id"]).to_csv(
        output_dir / "label_links.csv", index=False, lineterminator="\n"
    )
    candidates.sort_values(["left_index", "distance_arcsec", "right_index"]).to_csv(
        output_dir / "predicted_candidates.csv", index=False, lineterminator="\n"
    )
    controls.sort_values("parent_case_id").to_csv(
        output_dir / "shifted_controls.csv", index=False, lineterminator="\n"
    )
    control_candidates.sort_values(["left_index", "distance_arcsec", "right_index"]).to_csv(
        output_dir / "shifted_control_candidates.csv", index=False, lineterminator="\n"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )

    finished_utc = datetime.now(UTC)
    manifest = {
        "schema_version": 1,
        "benchmark_id": "xmm-cosmos-irac-chandra-v1",
        "protocol_boundary": PROTOCOL_BOUNDARY,
        "run_commit": git_commit,
        "started_utc": started_utc.isoformat(),
        "finished_utc": finished_utc.isoformat(),
        "elapsed_seconds": (finished_utc - started_utc).total_seconds(),
        "inputs": input_manifest,
        "outputs": {
            path.name: {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(output_dir.iterdir())
            if path.name != "manifest.json"
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ["astrobridge", "astropy", "numpy", "pandas", "scipy"]
            },
        },
        "source_pages": {
            "nway": "https://github.com/JohannesBuchner/nway",
            "marchesi_catalog": ("https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJ/817/34"),
            "nway_paper": ("https://academic.oup.com/mnras/article/473/4/4937/4554396"),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the prospectively specified XMM-COSMOS--IRAC benchmark."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/xmm_cosmos_v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/benchmark_data/xmm_cosmos_v1"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    metrics = run(args.raw_dir, args.output_dir)
    primary = metrics["raw_test_primary"]
    print(
        json.dumps(
            {
                "decision_rule_passed": metrics["decision_rule"]["passed"],
                "test_cases": primary["counts"]["strict_cases"],
                "candidate_coverage": primary["candidate_generation"]["candidate_coverage"][
                    "value"
                ],
                "precision": primary["decision"]["precision"]["value"],
                "recall": primary["decision"]["recall"]["value"],
                "calibration_intercept": metrics["calibration_fit"]["logit_intercept"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
