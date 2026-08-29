# AstroBridge

[![CI](https://github.com/VictorGSoutoXP/AstroBridge/actions/workflows/ci.yml/badge.svg)](https://github.com/VictorGSoutoXP/AstroBridge/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status: Research Alpha](https://img.shields.io/badge/status-research%20alpha-orange)

AstroBridge is an open research package for traceable probabilistic point-source
cross-identification in astronomical catalogs. The current development version focuses on
Gaia DR3 and AllWISE positional association; TESS inspection and novelty detection remain
exploratory notebook work.

> **Scientific status:** an independent Chandra-anchored XMM-COSMOS--IRAC benchmark confirmed
> complete candidate generation and strong ranking, but the frozen decision rule failed on
> recall and shifted controls. The project must not be described as NASA-validated,
> source-level calibrated, or publication-ready.

## Implemented in the package

- Query Gaia DR3 and AllWISE over a sky region.
- Propagate Gaia positions from J2016.0 to the AllWISE epoch using proper motion.
- Propagate independent per-axis position and proper-motion uncertainties to the target epoch.
- Exclude Gaia rows without both proper-motion components from the propagated match rather
  than treating missing motion as a precise zero.
- Generate **every** candidate pair inside a configurable angular radius.
- Compute the Budavári-Szalay positional Bayes factor after converting arcseconds to radians.
- Estimate explicit finite-footprint prior odds, normalized for the analytic all-sky Bayes
  factor, from field density and an expected association fraction.
- Resolve one-to-one associations by maximizing threshold-relative log-odds with the Hungarian
  algorithm on local connected components.
- Allow a source to remain unmatched when no candidate reaches the posterior threshold.
- Optionally label selected sources through SIMBAD.

The pair scores are binary match-versus-nonmatch posteriors; they are not calibrated marginal
probabilities across mutually exclusive candidates. The package currently assumes independent
circularized Gaussian errors and uses 2010.5 as a single nominal AllWISE epoch. Per-source
observation epochs, parallax displacement, full Gaia covariance, photometric priors, selection
functions, and calibrated novelty detection are roadmap items.

## Validation boundaries

### Synthetic association benchmark

The reproducible benchmark contains known associations and unmatched contaminants. With 200
true pairs and 40 contaminants in each catalog it produced:

| Field radius | Candidate pairs | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|
| 0.20 deg | 200 | 1.000 | 1.000 | 1.000 |
| 0.02 deg | 246 | 0.995 | 0.985 | 0.990 |
| 0.01 deg | 376 | 0.953 | 0.920 | 0.936 |

See [`reports/SYNTHETIC_VALIDATION.md`](reports/SYNTHETIC_VALIDATION.md) for configuration,
limitations, and reproduction commands. These results validate software behavior under the
simulation assumptions; they are not a substitute for an external survey benchmark.

### NGC 2516 membership diagnostic

The earlier notebook compared a deterministic NGC 2516 membership cut with the
Cantat-Gaudin & Anders (2020) candidate list. Its F1 score of 0.923 does **not** validate the
Gaia-AllWISE associations:

- the comparison contains 252 positives and 43 threshold-defined negatives;
- 294 of 295 sources were predicted as members;
- an always-member baseline already has F1 = 0.921;
- specificity is 0.023 and balanced accuracy is 0.512.

The corrected interpretation is documented in
[`reports/VALIDATION_REPORT.md`](reports/VALIDATION_REPORT.md). The notebook remains useful as
an exploratory membership diagnostic, not as cross-match ground truth.

### Official Gaia DR3-AllWISE algorithm comparison

An internally specified ten-field comparison, with three pre-fix executions explicitly
invalidated and all ten fields run from the corrected `b5f74ca` boundary, found all 209
least-ambiguous official associations inside the AstroBridge candidate sets. At the primary
0.5 threshold, AstroBridge selected the same counterpart for 178, selected no different
counterpart, and left 31 official candidates unselected. Agreement was 85.2% with a
descriptive Wilson 95% interval of
79.7%--89.3%; the frozen engineering rule required its lower bound to be at least 90%, so the
study **failed** that criterion. Agreement varied from 60.0% to 100.0% across the nine fields
with a defined rate.

This establishes complete candidate coverage for the strict positive subset and exposes a
field-dependent selection problem. Source density is a plausible contributor that still
requires a pre-specified stratified test. This study does not measure precision,
false-positive rate, calibration, or ground-truth accuracy. See
[`reports/GAIA_ALLWISE_CONFIRMATORY_RESULTS.md`](reports/GAIA_ALLWISE_CONFIRMATORY_RESULTS.md)
and the frozen/amended
[`docs/GAIA_ALLWISE_CONFIRMATORY_PROTOCOL.md`](docs/GAIA_ALLWISE_CONFIRMATORY_PROTOCOL.md).
The earlier exploratory table is retained as an explicitly invalidated historical artifact.

### Chandra-anchored XMM-COSMOS--IRAC benchmark

A prospectively specified independent benchmark used XMM positions as inputs and secure IRAC
counterparts established from higher-resolution Chandra COSMOS-Legacy sources as references.
After excluding incomplete one-to-one components, the untouched test split contained 1,050
strict references. AstroBridge generated all 1,050 truth candidates and ranked 1,003 first.
At the frozen 0.5 threshold it made 922 correct selections, 28 wrong selections, and 100
abstentions: precision was 97.05%, recall 87.81%, and F1 92.20%.

The primary engineering rule **failed** because recall was below 95% and 156 of 853 shifted
pseudo-negative controls received a selection (18.29%, versus a maximum of 5%). A pre-declared
intercept-only calibration raised recall to 93.14% but worsened control selection to 30.72%.
This supports the candidate generator and positional ranking in COSMOS while rejecting the
current binary pair posterior as a sufficient source-level decision probability. See the
[`results report`](reports/XMM_COSMOS_BENCHMARK_RESULTS.md), frozen
[`protocol`](docs/XMM_COSMOS_BENCHMARK_PROTOCOL.md), and machine-readable
[`artifacts`](reports/benchmark_data/xmm_cosmos_v1/).

## Installation

```bash
git clone https://github.com/VictorGSoutoXP/AstroBridge.git
cd AstroBridge

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"
```

To run the legacy exploratory notebooks, install their heavier optional dependencies with
`pip install -e ".[dev,notebooks]"`.

## Run the association pipeline

The command below performs live catalog and SIMBAD queries:

```bash
astrobridge \
  --ra 119.50 \
  --dec -60.83 \
  --radius 0.30 \
  --threshold-arcsec 2.0 \
  --min-posterior 0.5 \
  --expected-match-fraction 0.7 \
  --out data/processed/ngc2516_matches.csv
```

The expected association fraction is a model assumption, not a learned constant. Scientific
analyses should report sensitivity to this prior, the candidate radius, and the posterior
threshold.

## Run offline validation

```bash
ruff check src tests scripts
ruff format src tests scripts --check
pytest tests/

astrobridge-validate --field-radius-deg 0.02

astrobridge-reference-validate --ra 119.5 --dec -60.83 --radius 0.05
```

All automated tests are deterministic and make no network requests. Live service checks belong
in a separate opt-in integration workflow.

## Exploratory notebooks

Run `jupyter lab` and open:

1. `notebooks/01_ngc2516_xmatch_v3.ipynb` — original Gaia-AllWISE-TESS exploration.
2. `notebooks/02_validacao_cantat_gaudin.ipynb` — restricted membership diagnostic.

The notebooks predate the `0.2.0.dev0` package engine and are retained for provenance. Their
methods and claims should not be treated as identical to the current package until they are
refactored to call the tested API.

## Project layout

```text
AstroBridge/
├── data/                    # local raw, interim, and processed data
├── docs/                    # readiness and research documentation
├── notebooks/               # exploratory analyses with preserved outputs
├── reports/                 # validation reports and manuscript material
├── scripts/                 # reproducible command wrappers
├── src/astrobridge/         # importable package
├── tests/                   # offline deterministic tests
├── CITATION.cff
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
```

## Research roadmap

- [x] **Association engine:** multi-candidate search, positional Bayes factor, density prior,
  one-to-one resolution, and unmatched option.
- [x] **Deterministic validation:** unit tests and known-truth synthetic density stress test.
- [x] **External algorithm comparison:** internally specified held-out field study, rerun from
  a corrective boundary against the official Gaia DR3-AllWISE best-neighbour table; its
  primary decision rule failed.
- [x] **External association benchmark:** Chandra-anchored XMM-COSMOS--IRAC test completed with
  positives, ambiguity strata, shifted controls, frozen splits, and a failed primary rule.
- [x] **Pair-score diagnostics:** report pairwise reliability tables, Brier score, log loss,
  ECE, ranking, error/separation/density strata, and an intercept-only calibration test.
- [ ] **Source-level probability model:** normalize over all candidates plus `no counterpart`;
  learn the existence prior without using the spent COSMOS test split.
- [ ] **Additional held-out validation:** add independently established real unmatched cases,
  a new untouched field/catalog, and the official Gaia DR2-DR3 neighborhood mapping.
- [ ] **Sensitivity:** quantify candidate-radius, prior, and unmatched-decision sensitivity on
  development/calibration data only.
- [ ] **Astrometric model:** full covariance propagation, blending diagnostics, and selection
  functions.
- [ ] **FLINT-alpha:** only after association probabilities are independently calibrated,
  evaluate conditional density models for novelty ranking.
- [ ] **Archival release:** publish a versioned Zenodo record and DOI with reproducible inputs,
  tables, and figures.

The detailed submission checklist is in [`docs/NASA_READINESS.md`](docs/NASA_READINESS.md).
The [submission-path assessment](docs/NASA_SUBMISSION_PATH.md) explains eligibility and
NSPIRES gates, and the [concept note](docs/NASA_CONCEPT_NOTE.md) is explicitly an internal
draft rather than a proposal.

## Key references

- [Budavári, T. & Szalay, A. S. (2008)](https://arxiv.org/abs/0707.1611).
  *Probabilistic Cross-Identification of Astronomical Sources.* ApJ 679, 301.
- Pineau, F.-X., et al. (2017). *Probabilistic multi-catalogue positional cross-match.* A&A 597,
  A89.
- Salvato, M., et al. (2018). *Finding counterparts for all-sky X-ray surveys with NWAY.* MNRAS
  473, 4937.
- Marchesi, S., et al. (2016). *The Chandra COSMOS-Legacy Survey: Optical/IR
  Identifications.* ApJ 817, 34.
- Cantat-Gaudin, T. & Anders, F. (2020). *Clusters and mirages.* A&A 633, A99.
- Marrese, P. M., et al. (2019). *Gaia Data Release 2: Cross-match with external catalogues.*
  A&A 621, A144.

## License and citation

AstroBridge is released under the MIT License. Citation metadata is provided in
[`CITATION.cff`](CITATION.cff). A persistent DOI will be added after the first archival
release.

## Author

Victor Gonçalves Souto — data engineer and statistics graduate student; independent
contributor. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for collaboration guidance.
