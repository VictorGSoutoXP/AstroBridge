def test_package_imports_without_network_calls():
    import astrobridge.astrometry  # noqa: F401
    import astrobridge.bayes  # noqa: F401
    import astrobridge.matching  # noqa: F401
    import astrobridge.pipeline  # noqa: F401
