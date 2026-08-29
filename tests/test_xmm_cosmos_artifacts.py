import hashlib
import json
from pathlib import Path

import pandas as pd

BASE = Path("reports/benchmark_data/xmm_cosmos_v1")


def _load_json(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def test_xmm_cosmos_manifest_verifies_every_derived_artifact():
    manifest = _load_json("manifest.json")

    assert manifest["protocol_boundary"] == "dcf57d9c9bda375630566422de2b735af3c0166d"
    assert manifest["run_commit"] == "0220b3ef363300095f9c27f1ed59c4c466aa5947"
    for filename, metadata in manifest["outputs"].items():
        path = BASE / filename
        assert path.stat().st_size == metadata["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]


def test_xmm_cosmos_primary_counts_trace_to_committed_rows():
    metrics = _load_json("metrics.json")
    cases = pd.read_csv(BASE / "cases.csv", dtype={"case_id": "string"})
    candidates = pd.read_csv(
        BASE / "predicted_candidates.csv",
        dtype={"case_id": "string", "right_id": "string"},
    )
    controls = pd.read_csv(
        BASE / "shifted_controls.csv",
        dtype={"parent_case_id": "string"},
    )
    test_cases = cases.loc[cases["split"].eq("test")]
    test_candidates = candidates.loc[candidates["split"].eq("test")]

    assert len(test_cases) == 1_050
    assert test_cases["truth_in_candidates"].all()
    assert int(test_cases["correct_raw"].sum()) == 922
    assert int(test_candidates["selected_raw"].sum()) == 950
    assert int(controls["retained"].sum()) == 853
    assert int(controls["selected_raw"].sum()) == 156
    assert not test_candidates.loc[test_candidates["selected_raw"], "left_id"].duplicated().any()
    assert not test_candidates.loc[test_candidates["selected_raw"], "right_id"].duplicated().any()
    assert not metrics["decision_rule"]["passed"]


def test_xmm_cosmos_reference_and_closure_counts_are_preserved():
    cases = pd.read_csv(BASE / "cases.csv", dtype={"case_id": "string"})

    assert cases["truth_state"].value_counts().to_dict() == {
        "matched": 1_551,
        "unknown": 199,
        "ambiguous": 47,
    }
    assert int(cases["closure_excluded"].sum()) == 41
    assert int(cases["split"].eq("calibration").sum()) == 460
    assert int(cases["split"].eq("test").sum()) == 1_050
