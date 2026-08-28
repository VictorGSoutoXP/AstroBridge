# Confirmatory Gaia DR3-AllWISE agreement results

**Status:** completed; the pre-specified engineering decision rule did **not** pass.

This is a comparison with the official Gaia DR3-AllWISE cross-match algorithm, not an
independent truth validation. It measures whether AstroBridge generates and selects the same
counterpart in the deliberately least-ambiguous official subset.

## Audit boundaries and execution

- Original prospective internal boundary: `ca080e7c2f6c7e46a3f26b15d492b904b867f66a`
  at 2026-08-27 21:11:51 UTC. This was not a public, independent preregistration.
- Corrective internal boundary: `b5f74cad41ef4da9acdc93e51828ffff28ac681a`
  at 2026-08-28 18:04:13 UTC.
- Valid artifact-generation interval: 2026-08-28 18:05:12--18:09:01 UTC. These timestamps
  were recorded after each field's queries and processing; exact query start times were not
  captured.
- Successful fields: 10/10; Gaia-limit truncations: 0; post-fix service retries: 0.
- Every valid per-field JSON records the code commit, clean tracked-file state, dependency
  versions, exact Gaia/reference ADQL, AllWISE query parameters, effective prior odds, counts,
  and content hashes.

The first three pre-fix field outputs are retained under
`reports/benchmark_data/invalidated_pre_fix/` and excluded. They used a prior missing the
`1/(4*pi)` normalization and a probability-product assignment objective. The corrected code
uses finite-footprint odds scaled for the analytic all-sky Bayes factor and maximizes joint
log-odds with an unmatched option.

## Primary result: posterior threshold 0.5

| Field | Clean official | In candidates | Same counterpart | Different counterpart | Candidate not selected | Selections outside clean subset | Agreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| North Galactic Pole | 13 | 13 | 13 | 0 | 0 | 1 | 100.0% |
| South Galactic Pole | 14 | 14 | 13 | 0 | 1 | 0 | 92.9% |
| Galactic anticenter | 41 | 41 | 38 | 0 | 3 | 0 | 92.7% |
| Vela plane | 30 | 30 | 25 | 0 | 5 | 0 | 83.3% |
| Baade window | 12 | 12 | 9 | 0 | 3 | 0 | 75.0% |
| Orion nebula | 0 | 0 | 0 | 0 | 0 | 0 | N/A |
| LMC field | 30 | 30 | 19 | 0 | 11 | 4 | 63.3% |
| M31 field | 1 | 1 | 1 | 0 | 0 | 0 | 100.0% |
| Hyades | 53 | 53 | 51 | 0 | 2 | 0 | 96.2% |
| M4 | 15 | 15 | 9 | 0 | 6 | 0 | 60.0% |
| **Aggregate** | **209** | **209** | **178** | **0** | **31** | **5** | **85.2%** |

- Candidate coverage: 209/209 = 100.0%; descriptive Wilson 95% interval
  98.20%--100.00%.
- Same-counterpart agreement: 178/209 = 85.17%; descriptive Wilson 95% interval
  79.72%--89.35%.
- Across the nine fields with at least one clean reference, agreement ranged from 60.0% to
  100.0%, with an unweighted field mean of 84.83%.
- All 31 missed selections had the official counterpart inside the 2 arcsec candidate set.
  Their binary pair posteriors ranged from approximately 0.00019 to 0.43537.
- There were no different-counterpart selections to inspect. Whenever AstroBridge selected a
  source from the clean subset, it selected the same AllWISE designation as the official
  algorithm.

The five selections outside the clean subset are not labeled false positives. That category
contains sources deliberately excluded by the strict official-reference filter and is not a
negative truth class.

## Pre-declared secondary result: posterior threshold 0.1

| Field | Clean official | Same counterpart | Different counterpart | Candidate not selected | Selections outside clean subset | Agreement |
|---|---:|---:|---:|---:|---:|---:|
| North Galactic Pole | 13 | 13 | 0 | 0 | 1 | 100.0% |
| South Galactic Pole | 14 | 14 | 0 | 0 | 0 | 100.0% |
| Galactic anticenter | 41 | 40 | 0 | 1 | 0 | 97.6% |
| Vela plane | 30 | 25 | 0 | 5 | 0 | 83.3% |
| Baade window | 12 | 9 | 0 | 3 | 0 | 75.0% |
| Orion nebula | 0 | 0 | 0 | 0 | 0 | N/A |
| LMC field | 30 | 24 | 0 | 6 | 6 | 80.0% |
| M31 field | 1 | 1 | 0 | 0 | 0 | 100.0% |
| Hyades | 53 | 51 | 0 | 2 | 0 | 96.2% |
| M4 | 15 | 10 | 0 | 5 | 0 | 66.7% |
| **Aggregate** | **209** | **187** | **0** | **22** | **7** | **89.5%** |

The secondary agreement was 187/209 = 89.47%, with a descriptive Wilson 95% interval of
84.58%--92.95%. Its unweighted field mean was 88.75% and its field range was 66.7%--100.0%.
It recovered nine primary misses but left 22 unselected and increased selections outside the
clean subset from five to seven. This does not establish that 0.1 is a calibrated or preferable
production threshold.

## Frozen decision rule

| Criterion | Required | Observed | Outcome |
|---|---:|---:|---|
| Aggregate candidate coverage | at least 0.95 | 1.000 | Pass |
| Lower Wilson bound for primary agreement | at least 0.90 | 0.797 | **Fail** |
| Inspect every different-counterpart selection | all | none occurred | Pass |

The engineering comparator therefore **failed its pre-specified decision rule**. The failure
is informative: candidate generation and epoch-aware query coverage were complete for this
positive reference subset, while the fixed posterior-selection rule was too conservative and
its agreement varied substantially by field after correcting its normalization. Source density
is a plausible explanation, but this design did not isolate its effect.

## What is solid, and what is not

Supported by this study:

- all 209 least-ambiguous official counterparts were generated as candidates;
- no selected clean reference used a different AllWISE counterpart;
- the current posterior threshold produced substantially different agreement rates across the
  tested fields and did not satisfy the aggregate decision rule;
- the normalization and assignment defects materially changed the earlier exploratory claim.

Not supported:

- precision, recall, accuracy, false-positive rate, posterior calibration, or all-sky
  performance;
- performance on blends, multiple neighbours, Gaia mates, sources without proper motion, or
  the extreme-proper-motion Proxima case absent from this official reference table;
- robust nearby-source astrometry, because full Gaia covariance, parallax displacement,
  per-observation AllWISE epochs, and blending are not modeled;
- independent scientific validation or readiness for a NASA submission.

The Wilson intervals are descriptive by source. Spatial clustering and one-to-one assignment
create dependence, and dense fields can dominate the micro-average. Orion contained no clean
official association and was retained as specified.

## Reproduce and inspect

- Frozen protocol: `docs/GAIA_ALLWISE_CONFIRMATORY_PROTOCOL.md`
- Machine-readable aggregate: `reports/benchmark_data/confirmatory_summary.json`
- Per-field JSON and comparison CSV: `reports/benchmark_data/`
- Aggregator: `scripts/summarize_gaia_allwise_confirmatory.py`
- Invalidated pre-fix audit trail: `reports/benchmark_data/invalidated_pre_fix/`

```bash
python scripts/summarize_gaia_allwise_confirmatory.py \
  --expected-commit b5f74cad41ef4da9acdc93e51828ffff28ac681a \
  --output reports/benchmark_data/confirmatory_summary.json
```

Primary sources: [Budavári & Szalay (2008)](https://arxiv.org/abs/0707.1611),
[Gaia DR3 AllWISE best-neighbour documentation](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_cross-matches/ssec_dm_allwise_best_neighbour.html),
and [Gaia DR3 AllWISE cross-match DOI](https://doi.org/10.17876/gaia/dr.3/29).
