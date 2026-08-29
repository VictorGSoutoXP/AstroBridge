from pathlib import Path
from runpy import run_path

import pandas as pd

_SCRIPT = run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "run_xmm_cosmos_benchmark.py")
)
attach_case_outcomes = _SCRIPT["_attach_case_outcomes"]


def test_abstention_is_counted_as_incorrect_without_nullable_boolean():
    cases = pd.DataFrame(
        [
            {
                "case_id": "1",
                "left_id": "1",
                "truth_state": "matched",
                "truth_complete": True,
            }
        ]
    )
    truth = pd.DataFrame([{"case_id": "1", "right_id": "truth", "relation": "unique_true"}])
    candidates = pd.DataFrame(
        [
            {
                "case_id": "1",
                "right_id": "truth",
                "distance_arcsec": 1.0,
                "selected_raw": False,
                "selected_calibrated": False,
            }
        ]
    )

    outcome = attach_case_outcomes(cases, truth, candidates).iloc[0]

    assert outcome["truth_in_candidates"]
    assert not outcome["correct_raw"]
    assert not outcome["correct_calibrated"]
    assert pd.isna(outcome["selected_right_id_raw"])
