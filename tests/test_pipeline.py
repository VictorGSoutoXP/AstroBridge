import pytest

from astrobridge.pipeline import expanded_catalog_radius_deg


def test_expanded_catalog_radius_includes_candidate_margin():
    assert expanded_catalog_radius_deg(0.3, 2.0) == pytest.approx(0.3 + 2.0 / 3600.0)


def test_expanded_catalog_radius_rejects_invalid_geometry():
    with pytest.raises(ValueError, match="candidate_radius_arcsec"):
        expanded_catalog_radius_deg(0.3, 0.0)
