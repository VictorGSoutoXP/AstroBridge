# AstroBridge

[![CI](https://github.com/VictorGSoutoXP/AstroBridge/actions/workflows/ci.yml/badge.svg)](https://github.com/VictorGSoutoXP/AstroBridge/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status: Research Alpha](https://img.shields.io/badge/status-research%20alpha-orange)

AstroBridge is an open research package for traceable probabilistic point-source
cross-identification in astronomical catalogs. The current development version focuses on
Gaia DR3 and AllWISE positional association; TESS inspection and novelty detection remain
exploratory notebook work.

> **Scientific status:** the association engine has deterministic unit tests and a synthetic
> benchmark with known truth. Independent real-sky association validation is still pending.
> The project must not yet be described as NASA-validated or publication-ready.

## Implemented in the package

- Query Gaia DR3 and AllWISE over a sky region.
- Propagate Gaia positions from J2016.0 to the AllWISE epoch using proper motion.
- Propagate independent per-axis position and proper-motion uncertainties to the target epoch.
- Exclude Gaia rows without both proper-motion components from the propagated match rather
  than treating missing motion as a precise zero.
- Generate **every** candidate pair inside a configurable angular radius.
- Compute the Budavári-Szalay positional Bayes factor after converting arcseconds to radians.
- Estimate explicit prior odds from field density and an expected association fraction.
- Resolve one-to-one associations with the Hungarian algorithm on local connected components.
- Allow a source to remain unmatched when no candidate reaches the posterior threshold.
- Optionally label selected sources through SIMBAD.

The package currently assumes independent circularized Gaussian errors and uses 2010.5 as a
single nominal AllWISE epoch. Per-source observation epochs, full Gaia covariance, photometric
priors, selection functions, and calibrated novelty detection are roadmap items.

## Validation boundaries

### Synthetic association benchmark

The reproducible benchmark contains known associations and unmatched contaminants. With 200
true pairs and 40 contaminants in each catalog it produced:

| Field radius | Candidate pairs | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|
| 0.20 deg | 200 | 1.000 | 1.000 | 1.000 |
| 0.02 deg | 246 | 0.990 | 0.990 | 0.990 |
| 0.01 deg | 376 | 0.941 | 0.950 | 0.945 |

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
- [ ] **External association benchmark:** reproduce NWAY on XMM-COSMOS or another published
  truth set.
- [ ] **Held-out sky validation:** evaluate multiple clusters/fields and the official Gaia
  DR2-DR3 neighborhood mapping.
- [ ] **Calibration:** reliability curves, Brier score, expected calibration error, and prior
  sensitivity.
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
