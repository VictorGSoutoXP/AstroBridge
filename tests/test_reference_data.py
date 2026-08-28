import re

import pandas as pd

from astrobridge import data


class FakeResults:
    def __init__(self, frame):
        self.frame = frame

    def to_pandas(self):
        return self.frame


class FakeJob:
    def __init__(self, frame):
        self.frame = frame

    def get_results(self):
        return FakeResults(self.frame)


def test_fetch_reference_batches_source_ids(monkeypatch):
    queries = []

    def fake_launch(query):
        queries.append(query)
        identifiers = [
            int(value) for value in re.search(r"IN \(([^)]+)\)", query).group(1).split(",")
        ]
        frame = pd.DataFrame(
            {
                "source_id": identifiers,
                "original_ext_source_id": [f"J{value}" for value in identifiers],
                "angular_distance": 0.1,
                "xm_flag": 8,
                "allwise_oid": identifiers,
                "number_of_neighbours": 1,
                "number_of_mates": 0,
            }
        )
        return FakeJob(frame)

    monkeypatch.setattr(data.Gaia, "launch_job_async", fake_launch)

    result = data.fetch_gaia_allwise_best_neighbours([1, 2, 2, 3], chunk_size=2)

    assert len(queries) == 2
    assert list(result["source_id"]) == [1, 2, 3]
