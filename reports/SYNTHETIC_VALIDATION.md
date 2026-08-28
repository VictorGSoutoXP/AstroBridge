# Synthetic association validation

**Status:** deterministic engineering benchmark; not an external scientific validation.

**Corrected run:** implementation commit `b5f74ca`. Earlier dense-field numbers used a
finite-footprint prior that was missing the `1/(4*pi)` normalization and are superseded by
the table below.

This benchmark creates two catalogs with traceable one-to-one associations, adds unmatched
sources to both catalogs, perturbs positions with known Gaussian errors, and runs the same
candidate generation, Bayesian scoring, and uniqueness resolution used by the package.

## Configuration

- Random seed: 42
- True associations: 200
- Left-only contaminants: 40
- Right-only contaminants: 40
- Left positional uncertainty: 0.05 arcsec
- Right positional uncertainty: 0.30 arcsec
- Candidate radius: 2.0 arcsec
- Minimum posterior: 0.5

## Results

| Field radius | Candidate pairs | Selected | Correct | Incorrect | Missed | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.20 deg | 200 | 200 | 200 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 0.02 deg | 246 | 198 | 197 | 1 | 3 | 0.995 | 0.985 | 0.990 |
| 0.01 deg | 376 | 193 | 184 | 9 | 16 | 0.953 | 0.920 | 0.936 |

The dense-field degradation is expected and useful: positional evidence alone becomes
ambiguous as unrelated sources enter the candidate radius. It demonstrates why performance
must be reported as a function of source density and why photometric priors or richer
astrometric covariance will be needed for crowded fields.

## Reproduce

```bash
pip install -e ".[dev]"

astrobridge-validate --field-radius-deg 0.2
astrobridge-validate --field-radius-deg 0.02
astrobridge-validate --field-radius-deg 0.01
```

The implementation is in `src/astrobridge/validation.py`. Machine-readable outputs are in
`reports/synthetic_data/`. The automated test uses a smaller fixed simulation and asserts
minimum precision and recall.

## What this does not establish

- It does not validate associations in Gaia, AllWISE, TESS, or another real survey.
- It assumes independent circular Gaussian positional errors.
- It uses the true association fraction to set the density prior.
- It does not model catalog selection functions, blending, artifacts, or spatially varying
  uncertainty.

External benchmarks and held-out sky fields remain required before publication or proposal
claims are made.
