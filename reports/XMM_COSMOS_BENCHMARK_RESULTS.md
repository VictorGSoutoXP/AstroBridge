# XMM-COSMOS--IRAC independent benchmark results

**Status:** completed; the pre-specified primary engineering decision rule **failed**.

This experiment used lower-resolution XMM-COSMOS positions as AstroBridge inputs and secure
IRAC counterparts anchored by the higher-resolution Chandra COSMOS-Legacy catalog as the
independent reference. It is a real-sky association benchmark in one deep extragalactic field,
not an all-sky validation or a NASA-readiness claim.

## Audit boundary and reproducibility

- Internal prospective boundary: `dcf57d9c9bda375630566422de2b735af3c0166d`.
- First runner commit: `ccaaf21`; its first execution aborted before writing metrics because a
  nullable abstention flag could not be converted to an integer.
- Software-only abstention correction and first successful scientific run commit:
  `699cf2a522a3cd5a7d2d3122f27cf244fb8cc193`.
- The aborted attempt exposed no scientific result. The protocol records the correction; no
  input, label, split, model setting, threshold, metric, or gate changed.
- Artifact-normalization commit `0220b3ef363300095f9c27f1ed59c4c466aa5947` forced LF in
  generated CSVs so manifest hashes remain valid after Git checkout. It changed no scientific
  value; the final manifest records this commit.
- A second clean execution from `0220b3e` reproduced every scientific CSV and `metrics.json`
  byte for byte.
- The artifact manifest records source URLs, SHA-256 hashes, byte and row counts, schemas,
  file times, Python and dependency versions, OS, run times, code commit, and output hashes.

The three raw FITS inputs are not committed. Their verified hashes are:

| Input | Rows | SHA-256 |
|---|---:|---|
| NWAY `COSMOS_XMM.fits` | 1,797 | `9b2728376ff1b3f265923a2b7d2cd5a1f94da67739ef8eee308078017ac1a970` |
| NWAY `COSMOS_IRAC.fits` | 345,512 | `7db44b04fe8fcffc87087f8586e31c766128e4343d86a9fb2aca85e1ed9ec274` |
| Chandra COSMOS-Legacy counterparts | 4,016 | `3a9eab9fc7244d444b0500ebcdfa4b20aeda520dd29114ea5a1b9d1b1e16c5f2` |

The NWAY files were pinned to upstream commit
`a37be1f9402ea2e7d6ff5f022f5f23ad94ff15fc`.

## Reference construction

Of the 1,797 XMM sources:

| Reference state | Cases | Treatment |
|---|---:|---|
| Secure unique Chandra--IRAC reference | 1,551 | eligible for strict metrics |
| Ambiguous | 47 | descriptive set-valued analysis only |
| Unknown/incomplete | 199 | excluded from strict metrics |

The 47 ambiguous cases comprise 31 XMM identifiers split into multiple Chandra sources, 15
Chandra final-identification flag `10` cases, and one secure Chandra position with two NWAY
IRAC sources inside the prospectively fixed 0.5-arcsec label-linking radius. The latter had
IRAC link separations of 0.000 and 0.140 arcsec and was conservatively not forced into a
unique label.

Forty-one otherwise secure cases shared a 20-arcsec bipartite candidate component with an
ambiguous or incomplete XMM case. They were excluded before strict evaluation so that an
unlabeled source could not take a counterpart away from a labeled source. The remaining
closed components produced 460 calibration cases and 1,050 untouched test cases. The test
set contained 968 closed components.

These are high-confidence references, not infallible ground truth. Chandra supplies much
sharper X-ray localization, while the published optical/IR identification still used
likelihood-ratio, multi-band, and visual information.

## Frozen primary result

Configuration: 20-arcsec candidates, XMM catalog positional errors, 0.5-arcsec IRAC error,
2.0-square-degree footprint, expected association fraction 0.9, binary pair-posterior
threshold 0.5, and the existing one-to-one resolver with an unmatched option.

| Outcome | Count/rate | Wilson 95% | Component bootstrap 95% |
|---|---:|---:|---:|
| Truth candidate present | 1,050/1,050 = **100.00%** | 99.64%--100.00% | 100.00%--100.00% |
| Correct selections (TP) | 922 | -- | -- |
| Wrong selections | 28 | -- | -- |
| Abstentions | 100 | -- | -- |
| Precision | 922/950 = **97.05%** | 95.77%--97.95% | 95.95%--98.07% |
| Recall / exact positive decision | 922/1,050 = **87.81%** | 85.69%--89.65% | 85.80%--89.76% |
| F1 | **92.20%** | -- | -- |
| Shifted-control selection | 156/853 = **18.29%** | 15.84%--21.02% | 15.68%--20.91% |

The shifted positions were 60 arcsec east of a test XMM source and were rejected if their
candidate circle crossed the IRAC rectangular bounds or their center lay within 20 arcsec of
any cataloged XMM or Chandra source. Of 1,050 constructed controls, 853 passed those checks.
They are pseudo-negatives, not proof of physical absence.

### Candidate ranking

Every strict reference was generated as a candidate. The truth-pair raw-posterior ranks were:

| Rank | Cases |
|---:|---:|
| 1 | 1,003 |
| 2 | 38 |
| 3 | 7 |
| 4 | 1 |
| 5 | 1 |

Thus 95.52% of references were the top-scored candidate; mean rank was 1.056 and median rank
was 1. Among the top-ranked truths, 922 were selected correctly and 81 were left unmatched.
All 28 wrong selections occurred among the 47 cases whose truth was not rank 1. This separates
two failure modes cleanly: threshold-driven abstention and candidate misranking.

### Pair-score diagnostics

On 14,385 generated test edges (1,050 positive and 13,335 negative):

| Metric | Micro by edge | Source-balanced |
|---|---:|---:|
| Average precision | 0.97197 | -- |
| Brier score | 0.01290 | 0.01364 |
| Binary log loss | 0.04715 | 0.04948 |
| Ten-bin ECE | 0.01994 | 0.02150 |

These metrics are conditional on the generated pair universe. The binary pair posteriors do
not sum to one over candidates plus an unmatched state, so the ECE and Brier scores must not
be interpreted as calibration of the final source-level assignment decision.

## Pre-declared intercept-only calibration

The calibration split contained 460 true edges and 5,888 negative candidate edges. Fitting
the one permitted additive logit intercept produced `delta = 0.633131`, multiplying raw pair
odds by about 1.88 while preserving every rank.

| Test outcome | Raw primary | Intercept-calibrated secondary |
|---|---:|---:|
| Selected associations | 950 | 1,016 |
| Correct selections | 922 | 978 |
| Wrong selections | 28 | 38 |
| Abstentions | 100 | 34 |
| Precision | 97.05% | 96.26% |
| Recall | 87.81% | 93.14% |
| F1 | 92.20% | 94.68% |
| Micro Brier | 0.01290 | 0.01148 |
| Micro ECE | 0.01994 | 0.01705 |
| Shifted-control selection | 18.29% | **30.72%** |

The scalar correction improved pair loss and positive-case recall, but it increased wrong
selections and made the shifted-control behavior substantially worse. It therefore does not
solve the missing source-level `no counterpart` probability.

## Frozen strata and ambiguities

Quartile boundaries were derived on the calibration split and then applied to the test split.
Candidate coverage stayed 100% in every stratum.

| Test quartile | Raw recall by XMM error | Raw recall by truth separation | Raw recall by candidate count |
|---:|---:|---:|---:|
| Q1 | 97.86% | 100.00% | 88.73% |
| Q2 | 96.76% | 99.62% | 87.29% |
| Q3 | 89.57% | 98.52% | 88.83% |
| Q4 | **65.31%** | **49.80%** | 86.73% |

The strongest degradation is associated with larger XMM positional errors and larger
XMM--truth separations, not with the candidate-count quartiles used here. In the 128 primary
test cases that were not correct, median XMM error was 2.246 arcsec and median truth separation
was 3.230 arcsec; the corresponding medians for correct cases were 1.680 and 1.077 arcsec.

Among the 47 ambiguous cases, 46 had at least one reference-linked IRAC set. All reference
IRAC members were present in the candidate set for all 46; the primary resolver abstained on
18 of the 47. These cases were never forced into TP/FP counts.

## Frozen decision rule

| Criterion | Required | Observed | Outcome |
|---|---:|---:|---|
| Candidate coverage, point | at least 0.98 | 1.000 | Pass |
| Candidate coverage, bootstrap lower bound | at least 0.95 | 1.000 | Pass |
| Precision, point | at least 0.95 | 0.971 | Pass |
| Precision, bootstrap lower bound | at least 0.90 | 0.960 | Pass |
| Recall, point | at least 0.95 | 0.878 | **Fail** |
| Recall, bootstrap lower bound | at least 0.90 | 0.858 | **Fail** |
| Shifted-control selection, point | at most 0.05 | 0.183 | **Fail** |
| Shifted-control selection, bootstrap upper bound | at most 0.10 | 0.209 | **Fail** |

The limited benchmark therefore **failed**. Bootstrap intervals quantify within-COSMOS
component variation only; one field cannot support sky-to-sky generalization.

## What this study establishes

- The 20-arcsec generator did not lose any of the 1,050 untouched strict references.
- Positional ranking is strong in this one field: 95.52% truth rank 1 and pairwise average
  precision 0.972.
- The fixed source decision is not adequate: recall is below the frozen target and the
  shifted-control selection rate is far above it.
- A global pairwise intercept cannot resolve the tradeoff. It recovers positive matches by
  selecting more at arbitrary control positions.
- Large XMM errors and separations identify the dominant positive-case failure regime.

The coherent next model is not another threshold search on this test set. It is a normalized
source-level distribution over `{candidate 1, ..., candidate k, no counterpart}`, with an
explicit source-existence prior and calibration against independently labeled matched and
unmatched cases. Any revised model needs a new untouched field or catalog for its final test;
the COSMOS test split is now spent.

This result is useful enough to continue the software research, but it rejects the current
claim that `posterior_match` is sufficient for final association decisions. If the project is
not going to implement and independently test that architectural change, the scientifically
honest action is to archive it as a well-documented negative result rather than submit it to
NASA.

## Reproduce and inspect

```bash
python scripts/run_xmm_cosmos_benchmark.py
```

- Protocol: `docs/XMM_COSMOS_BENCHMARK_PROTOCOL.md`
- Manifest and metrics: `reports/benchmark_data/xmm_cosmos_v1/manifest.json` and
  `reports/benchmark_data/xmm_cosmos_v1/metrics.json`
- Cases, truth pairs, candidates, controls, and label links:
  `reports/benchmark_data/xmm_cosmos_v1/`

Primary sources:

- [Salvato et al. (2018), NWAY and its XMM-COSMOS/Chandra validation](https://academic.oup.com/mnras/article/473/4/4937/4554396)
- [Marchesi et al. (2016), Chandra COSMOS-Legacy optical/IR identifications](https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJ/817/34)
- [NWAY source repository and released example catalogs](https://github.com/JohannesBuchner/nway)
- [NASA/IPAC COSMOS archive overview](https://irsa.ipac.caltech.edu/data/COSMOS/overview.html)
