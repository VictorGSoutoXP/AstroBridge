import pandas as pd

from astrobridge.simbad import add_simbad_flags


class FailingSimbad:
    def add_votable_fields(self, *fields):
        return None

    def query_region(self, *args, **kwargs):
        raise RuntimeError("offline")


def test_simbad_query_failure_is_not_reported_as_no_match(monkeypatch):
    monkeypatch.setattr("astrobridge.simbad.Simbad", FailingSimbad)
    matches = pd.DataFrame({"gaia_ra": [10.0], "gaia_dec": [0.0]})

    result = add_simbad_flags(matches)

    assert pd.isna(result.loc[0, "known_in_simbad"])
    assert result.loc[0, "simbad_query_status"] == "error"


def test_simbad_limit_marks_unqueried_rows(monkeypatch):
    monkeypatch.setattr("astrobridge.simbad.Simbad", FailingSimbad)
    matches = pd.DataFrame({"gaia_ra": [10.0, 11.0], "gaia_dec": [0.0, 0.0]})

    result = add_simbad_flags(matches, limit=0)

    assert result["known_in_simbad"].isna().all()
    assert set(result["simbad_query_status"]) == {"not_queried"}
