from astrobridge.validation import run_synthetic_benchmark


def test_synthetic_benchmark_recovers_known_associations():
    metrics = run_synthetic_benchmark(
        n_associations=80,
        n_left_only=20,
        n_right_only=20,
        seed=7,
    )

    assert metrics.precision >= 0.95
    assert metrics.recall >= 0.95
    assert metrics.correct_associations <= metrics.true_associations
    assert metrics.incorrect_associations >= 0
