from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from astrobridge.matching import CrossmatchResult


@dataclass(frozen=True)
class ReferenceAgreementMetrics:
    """Agreement diagnostics against the official Gaia DR3-AllWISE cross-match."""

    gaia_sources: int
    allwise_sources: int
    candidate_pairs: int
    selected_associations: int
    official_associations: int
    clean_official_associations: int
    reference_in_candidate_set: int
    reference_missing_from_candidates: int
    agreements: int
    disagreements: int
    reference_not_selected: int
    selected_without_clean_reference: int
    candidate_coverage: float
    agreement_rate_on_clean_reference: float
    agreement_when_selected: float
    selection_given_reference_candidate: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def clean_gaia_allwise_reference(reference: pd.DataFrame) -> pd.DataFrame:
    """Return the least ambiguous official associations for agreement analysis.

    ``xm_flag == 8`` selects five-parameter Gaia solutions without the duplicate,
    resolved-source, or special-treatment flags. Requiring one neighbour and no
    mates removes ambiguity on both sides of the association.
    """

    required = {
        "source_id",
        "original_ext_source_id",
        "xm_flag",
        "number_of_neighbours",
        "number_of_mates",
    }
    missing = required.difference(reference.columns)
    if missing:
        raise ValueError(f"reference missing columns: {sorted(missing)}")

    clean = reference.loc[
        (pd.to_numeric(reference["xm_flag"], errors="coerce") == 8)
        & (pd.to_numeric(reference["number_of_neighbours"], errors="coerce") == 1)
        & (pd.to_numeric(reference["number_of_mates"], errors="coerce") == 0)
    ].copy()
    clean["source_id"] = pd.to_numeric(clean["source_id"], errors="raise").astype("int64")
    clean["original_ext_source_id"] = clean["original_ext_source_id"].astype("string").str.strip()
    return clean.drop_duplicates("source_id", keep="first").reset_index(drop=True)


def _safe_ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def gaia_allwise_reference_comparison(
    result: CrossmatchResult,
    gaia: pd.DataFrame,
    allwise: pd.DataFrame,
    reference: pd.DataFrame,
) -> pd.DataFrame:
    """Build one diagnostic row per clean official Gaia-AllWISE association."""

    if "source_id" not in gaia:
        raise ValueError("gaia must contain source_id")
    if "designation" not in allwise:
        raise ValueError("allwise must contain designation")

    clean = clean_gaia_allwise_reference(reference).rename(
        columns={
            "original_ext_source_id": "reference_designation",
            "angular_distance": "reference_distance_arcsec",
        }
    )
    if clean.empty:
        return clean.assign(
            candidate_present=pd.Series(dtype=bool),
            candidate_distance_arcsec=pd.Series(dtype=float),
            candidate_posterior=pd.Series(dtype=float),
            selected_designation=pd.Series(dtype="string"),
            selected_distance_arcsec=pd.Series(dtype=float),
            selected_posterior=pd.Series(dtype=float),
            status=pd.Series(dtype="string"),
        )

    candidate_lookup: dict[tuple[int, str], tuple[float, float]] = {}
    if not result.candidates.empty:
        for candidate in result.candidates.itertuples(index=False):
            source_id = int(gaia.iloc[int(candidate.left_index)]["source_id"])
            designation = str(allwise.iloc[int(candidate.right_index)]["designation"]).strip()
            candidate_lookup[(source_id, designation)] = (
                float(candidate.distance_arcsec),
                float(candidate.posterior_match),
            )

    selected_lookup: dict[int, tuple[str, float, float]] = {}
    if not result.matches.empty:
        required_matches = {
            "gaia_source_id",
            "wise_designation",
            "distance_arcsec",
            "posterior_match",
        }
        missing_matches = required_matches.difference(result.matches.columns)
        if missing_matches:
            raise ValueError(f"matches missing columns: {sorted(missing_matches)}")
        for match in result.matches.itertuples(index=False):
            selected_lookup[int(match.gaia_source_id)] = (
                str(match.wise_designation).strip(),
                float(match.distance_arcsec),
                float(match.posterior_match),
            )

    gaia_by_source = gaia.copy()
    gaia_by_source["source_id"] = gaia_by_source["source_id"].astype("int64")
    gaia_by_source = gaia_by_source.drop_duplicates("source_id").set_index("source_id")
    rows = []
    for reference_row in clean.itertuples(index=False):
        source_id = int(reference_row.source_id)
        reference_designation = str(reference_row.reference_designation).strip()
        gaia_row = gaia_by_source.loc[source_id]
        candidate = candidate_lookup.get((source_id, reference_designation))
        selected = selected_lookup.get(source_id)
        if candidate is None and selected is not None:
            status = "disagreement_reference_missing_from_candidates"
        elif candidate is None:
            status = "missing_from_candidates"
        elif selected is None:
            status = "candidate_not_selected"
        elif selected[0] == reference_designation:
            status = "agreement"
        else:
            status = "disagreement"
        rows.append(
            {
                **reference_row._asdict(),
                "candidate_present": candidate is not None,
                "candidate_distance_arcsec": candidate[0] if candidate else None,
                "candidate_posterior": candidate[1] if candidate else None,
                "selected_designation": selected[0] if selected else None,
                "selected_distance_arcsec": selected[1] if selected else None,
                "selected_posterior": selected[2] if selected else None,
                "status": status,
                **{
                    f"gaia_{column}": gaia_row[column] if column in gaia_row else None
                    for column in (
                        "pmra",
                        "pmdec",
                        "phot_g_mean_mag",
                        "ruwe",
                        "position_sigma_arcsec",
                    )
                },
            }
        )
    return pd.DataFrame(rows)


def evaluate_gaia_allwise_reference(
    result: CrossmatchResult,
    gaia: pd.DataFrame,
    allwise: pd.DataFrame,
    reference: pd.DataFrame,
) -> ReferenceAgreementMetrics:
    """Compare AstroBridge output with a clean subset of the official cross-match.

    This measures agreement with another algorithm, not scientific truth. The
    official reference itself balances completeness and correctness.
    """

    clean_reference = clean_gaia_allwise_reference(reference)
    reference_pairs = set(
        zip(
            clean_reference["source_id"].astype("int64"),
            clean_reference["original_ext_source_id"].astype(str),
            strict=True,
        )
    )
    reference_by_source = dict(reference_pairs)

    candidate_pairs: set[tuple[int, str]] = set()
    if not result.candidates.empty:
        left_indices = result.candidates["left_index"].to_numpy(dtype=int)
        right_indices = result.candidates["right_index"].to_numpy(dtype=int)
        candidate_pairs = set(
            zip(
                gaia.iloc[left_indices]["source_id"].astype("int64"),
                allwise.iloc[right_indices]["designation"].astype("string").str.strip(),
                strict=True,
            )
        )

    selected_by_source: dict[int, str] = {}
    if not result.matches.empty:
        required_matches = {"gaia_source_id", "wise_designation"}
        missing_matches = required_matches.difference(result.matches.columns)
        if missing_matches:
            raise ValueError(f"matches missing columns: {sorted(missing_matches)}")
        selected_by_source = dict(
            zip(
                result.matches["gaia_source_id"].astype("int64"),
                result.matches["wise_designation"].astype("string").str.strip(),
                strict=True,
            )
        )

    reference_in_candidates = sum(pair in candidate_pairs for pair in reference_pairs)
    agreements = sum(
        selected_by_source.get(source_id) == designation
        for source_id, designation in reference_pairs
    )
    disagreements = sum(
        source_id in selected_by_source and selected_by_source[source_id] != designation
        for source_id, designation in reference_pairs
    )
    not_selected = len(reference_pairs) - agreements - disagreements
    selected_without_reference = sum(
        source_id not in reference_by_source for source_id in selected_by_source
    )
    selected_for_reference = agreements + disagreements

    return ReferenceAgreementMetrics(
        gaia_sources=len(gaia),
        allwise_sources=len(allwise),
        candidate_pairs=len(result.candidates),
        selected_associations=len(result.matches),
        official_associations=len(reference),
        clean_official_associations=len(reference_pairs),
        reference_in_candidate_set=reference_in_candidates,
        reference_missing_from_candidates=len(reference_pairs) - reference_in_candidates,
        agreements=agreements,
        disagreements=disagreements,
        reference_not_selected=not_selected,
        selected_without_clean_reference=selected_without_reference,
        candidate_coverage=_safe_ratio(reference_in_candidates, len(reference_pairs)),
        agreement_rate_on_clean_reference=_safe_ratio(agreements, len(reference_pairs)),
        agreement_when_selected=_safe_ratio(agreements, selected_for_reference),
        selection_given_reference_candidate=_safe_ratio(agreements, reference_in_candidates),
    )
