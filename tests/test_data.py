import pandas as pd
import pytest

from astrobridge.data import fetch_gaia_allwise_best_neighbours, fetch_gaia_dr3


class _FakeResults:
    def __init__(self, frame):
        self.frame = frame

    def to_pandas(self):
        return self.frame.copy()


class _FakeJob:
    def __init__(self, frame):
        self.frame = frame

    def get_results(self):
        return _FakeResults(self.frame)


def test_gaia_query_is_ordered_and_detects_truncation(monkeypatch):
    captured = {}

    def fake_launch(query):
        captured["query"] = query
        return _FakeJob(pd.DataFrame({"source_id": [1, 2, 3]}))

    monkeypatch.setattr("astrobridge.data.Gaia.launch_job_async", fake_launch)

    result = fetch_gaia_dr3(10.0, -5.0, 0.1, limit=2)

    assert list(result["source_id"]) == [1, 2]
    assert result.attrs["gaia_query_limit_reached"] is True
    assert "SELECT TOP 3" in captured["query"]
    assert "ORDER BY source_id" in captured["query"]


@pytest.mark.parametrize("limit", [0, 1.5, True])
def test_gaia_query_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="positive integer"):
        fetch_gaia_dr3(10.0, -5.0, 0.1, limit=limit)


@pytest.mark.parametrize("source_id", [1.5, float(5853498713190525696), True])
def test_reference_query_rejects_inexact_source_identifiers(source_id):
    with pytest.raises(ValueError, match="exact non-negative integers"):
        fetch_gaia_allwise_best_neighbours([source_id])
