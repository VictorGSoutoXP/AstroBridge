# XMM-COSMOS--IRAC independent benchmark protocol

**Status:** internally specified before any AstroBridge score or selection was computed on
this benchmark. The first Git commit containing this file is the internal registration
boundary; its hash must be copied into the results report. This is not a public or independent
preregistration.

**Execution note (2026-08-29):** the first attempt from runner commit `ccaaf21` aborted before
writing any metrics or output artifacts. The aggregation code represented an abstention as a
nullable string and then attempted to cast its nullable equality result directly to an integer.
The traceback exposed no scientific outcome. The corrective change explicitly maps a missing
selection to `correct = false` and adds a regression test. No input, label, split, score,
threshold, exclusion, metric, or decision rule changed. The first successful run after this
documented software-only correction is the valid run.

**Artifact note:** the first successful scientific run from `699cf2a` wrote platform-native
line endings. Commits `0220b3e` and `0f234a8` fixed generated CSV and JSON artifacts to LF so
their manifest hashes survive Git checkout on every platform. They changed no data value or
metric. Two runs from `0f234a8`, including one from a clean clone, reproduced all scientific
artifacts byte for byte.

**Outcome:** the valid normalized run from `0f234a8` failed the frozen recall and shifted-
control criteria while passing candidate-coverage and precision criteria. See
`reports/XMM_COSMOS_BENCHMARK_RESULTS.md`.

## Question and scope

Test whether AstroBridge can recover independently established IRAC counterparts when given
the less precise XMM-COSMOS positions and positional uncertainties. Chandra COSMOS-Legacy
provides the higher-resolution reference positions used to establish the labels. The
experiment evaluates the positional association engine in one deep extragalactic field. It
does not validate Gaia--AllWISE epoch propagation, all-sky performance, or a NASA-ready
scientific product.

The primary analysis uses only positions and positional uncertainties. IRAC magnitudes,
NWAY output probabilities, the original XMM counterpart table, Chandra positions, and
identification flags are forbidden inputs to AstroBridge. They may be used only to construct
or audit reference labels after candidate scoring is complete.

## Frozen public inputs

The XMM and IRAC candidate catalogs are the example catalogs released by the NWAY authors at
Git commit `a37be1f9402ea2e7d6ff5f022f5f23ad94ff15fc`:

- `COSMOS_XMM.fits`: 1,797 rows; SHA-256
  `9b2728376ff1b3f265923a2b7d2cd5a1f94da67739ef8eee308078017ac1a970`;
- `COSMOS_IRAC.fits`: 345,512 rows; SHA-256
  `7db44b04fe8fcffc87087f8586e31c766128e4343d86a9fb2aca85e1ed9ec274`.

The files are retrieved from commit-pinned URLs under
`https://raw.githubusercontent.com/JohannesBuchner/nway/` rather than a moving branch. The
NWAY repository is AGPL-3.0, but that software license must not be represented as the catalog
data license. The results must cite Salvato et al. (2018) and the underlying COSMOS catalogs
and preserve the source URLs and checksums.

The reference catalog is the public IRSA file
`chandra_COSMOS_legacy_opt_NIR_counterparts_20160113_4d.fits`, described by Marchesi et al.
(2016). It contains Chandra X-ray positions, final counterpart-identification flags, IRAC
counterpart coordinates, and the XMM-COSMOS identifier. The run manifest must record its
download URL, byte count, SHA-256, schema, retrieval UTC time, and the relevant paper/bibcode.
No raw third-party catalog is committed to this repository.

Primary source pages:

- NWAY repository: <https://github.com/JohannesBuchner/nway>
- Chandra COSMOS-Legacy catalog: <https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJ/817/34>
- COSMOS archive overview: <https://irsa.ipac.caltech.edu/data/COSMOS/overview.html>
- NWAY validation paper: <https://academic.oup.com/mnras/article/473/4/4937/4554396>

## Reference construction

All identifiers are read as strings. Every XMM source is assigned one of four reference
states before evaluation:

1. **strict matched:** exactly one Chandra catalog row has the XMM identifier, its final
   identification flag is `1` (secure), it has finite Sanders-catalog IRAC coordinates, and
   exactly one NWAY IRAC source lies within 0.5 arcsec of those coordinates;
2. **ambiguous:** the XMM identifier maps to more than one Chandra source, the final flag is
   `10`, or more than one NWAY IRAC source lies within the 0.5-arcsec label-linking radius;
3. **subthreshold/unknown:** the final flag is `100` or `-99`, the XMM identifier is absent
   from Chandra, the required IRAC coordinates are missing, or no NWAY IRAC source is found
   within 0.5 arcsec; and
4. **shifted control:** a constructed stress-control position, never described as astronomical
   ground truth.

The 0.5-arcsec label-linking radius is fixed from the IRAC positional uncertainty used in the
published NWAY worked example. It is not selected from AstroBridge outcomes. A strict truth
right-hand source may not be reused by two XMM sources.

The Chandra labels are high-confidence references, not infallible ground truth: Marchesi et
al. used likelihood-ratio, multi-band, and visual information to identify counterparts.
Their independence here comes from the substantially sharper Chandra localization rather
than from a wholly model-free labeling process.

## Frozen AstroBridge configuration

- left positions and one-sigma circular errors: `RA`, `DEC`, and `pos_err` from
  `COSMOS_XMM.fits`;
- right positions: `RA` and `DEC` from `COSMOS_IRAC.fits`;
- right positional uncertainty: 0.5 arcsec for every IRAC row;
- common footprint: 2.0 square degrees from the released FITS metadata;
- candidate radius: 20 arcsec;
- expected association fraction for the finite-footprint prior: 0.9;
- primary minimum pair posterior: 0.5;
- assignment: the existing threshold-relative log-odds one-to-one resolver with an explicit
  unmatched option;
- inference features: positional separation and the stated errors only.

The 20-arcsec radius, 0.5-arcsec IRAC uncertainty, and 0.9 completeness assumption follow the
published NWAY COSMOS example. The 0.5 decision threshold is the existing AstroBridge default.
None may be changed after inspecting benchmark outcomes.

Candidate pairs are generated for all 1,797 real XMM sources before reference filtering. The
bipartite graph is divided into connected components. Strict decision and calibration metrics
include only components in which every XMM node has a complete strict label. A component that
contains an ambiguous, unknown, or incomplete case is excluded from strict metrics and
reported with its exclusion reason. This prevents an unlabeled source from taking a candidate
away from a scored source during one-to-one resolution.

The prior is computed once from the full XMM and IRAC counts and the 2.0-square-degree
footprint. Filtering strict components must not change it.

## Frozen calibration/test split

Eligible closed components, not individual candidate edges, are split deterministically.
For each component, sort its XMM IDs, join them with commas, prepend
`astrobridge-xmm-cosmos-v1|`, compute SHA-256, interpret the first eight bytes as an unsigned
integer, and take the value modulo 10:

- values 0--2: `calibration` (30% expected);
- values 3--9: `test` (70% expected).

No component may occur in both splits. The raw configuration is evaluated without fitting.
One secondary calibrated analysis is permitted: fit a single additive intercept `delta` on
the calibration split only,

`calibrated_logit = logit(posterior_match) + delta`,

by minimizing unweighted binary log loss over candidate pairs whose true candidate is
present. Clip raw probabilities to `[1e-12, 1 - 1e-12]` for this calculation. Preserve the
Bayes-factor ordering and fit no slope, magnitude term, density term, threshold grid, or other
hyperparameter. Apply the frozen fitted intercept once to the test split and rerun the
one-to-one resolver at 0.5. The uncalibrated test result remains primary.

## Shifted stress controls

For each strict real XMM source, construct one control 60 arcsec due east on the local tangent
plane. Reject it without replacement if its 20-arcsec candidate circle crosses the rectangular
RA/Dec bounds of the IRAC catalog or if its center lies within 20 arcsec of any real XMM or
Chandra X-ray position. Match all retained controls in a separate run with the identical IRAC
catalog, prior, errors, radius, threshold, and resolver. A selected IRAC source is counted as a
control false selection.

These controls test behavior at positions without a cataloged X-ray source after the stated
veto. They are pseudo-negatives, not proof that no physical counterpart exists, and they do
not enter strict precision, recall, pair calibration, or the primary success claim.

## Frozen outcomes

### Candidate generation

For strict matched test cases report:

- truth-candidate coverage and its denominator;
- truth-candidate rank by raw pair posterior;
- candidate-set size; and
- results by XMM error, local candidate density, and XMM--truth separation using quartile
  boundaries derived on the calibration split and then frozen.

### Pair score

On closed test components, label the unique reference edge positive and every other generated
edge negative. Report micro and source-balanced Brier score and binary log loss; a ten-bin
equal-width reliability table and expected calibration error; and average precision. These
are conditional on candidate generation. Missing true edges reduce candidate coverage and
must not be silently converted into negative edges.

`posterior_match` is a binary pair score. It is not a normalized marginal distribution over
mutually exclusive candidates plus an unmatched state. Consequently, no categorical Brier
score or claim that the selected posterior is a calibrated assignment probability is allowed.

### One-to-one decision

After resolving the full graph, use:

- `TP`: selected reference edges;
- `FP`: selected non-reference edges;
- `FN`: reference edges not selected; and
- `TN`: complete unmatched cases correctly left without a selection.

A wrong selection for a matched source contributes one FP and one FN. Report precision,
recall, F1, exact-decision accuracy, selection coverage, and abstention. The primary strict
set contains matched cases, so specificity and a real-negative false-positive rate are
undefined there rather than reported as zero. Report the shifted-control selection rate
separately.

Ambiguous and split XMM cases are descriptive only: report whether every reference-linked
IRAC source is present in the candidate set, whether at least one is present, and whether the
resolver abstains. Do not force a unique TP/FP label.

## Uncertainty and decision rule

Report Wilson 95% intervals for simple proportions and a 10,000-replicate percentile
bootstrap that resamples closed bipartite components, with seed `20260828`. The bootstrap
quantifies within-field sampling variation only. With one COSMOS field it cannot measure
field-to-field or all-sky uncertainty.

The uncalibrated primary system passes this limited engineering benchmark only if all of the
following hold on the untouched test split:

- truth-candidate coverage is at least 0.98 and its bootstrap 95% lower bound is at least
  0.95;
- selected-counterpart precision is at least 0.95 and its lower bound is at least 0.90;
- selected-counterpart recall is at least 0.95 and its lower bound is at least 0.90; and
- the shifted-control selection rate is at most 0.05 and its 95% upper bound is at most 0.10.

Calibration metrics and the secondary intercept correction are diagnostic in version 1 and
have no pass/fail cutoff. Passing cannot establish performance outside COSMOS or satisfy NASA
readiness. Failing must be reported; thresholds or priors may not be retuned on the test split.

## Reproducibility and failure handling

- Save a manifest with exact source URLs, checksums, sizes, row counts, schemas, UTC retrieval
  times, package versions, operating system, Python version, AstroBridge commit, protocol
  boundary, split seed/rule, fitted calibration intercept, and every exclusion count.
- Preserve cases, reference pairs, all scored candidates, selections, component IDs, split
  labels, and aggregate JSON under `reports/benchmark_data/xmm_cosmos_v1/`.
- Keep raw downloaded FITS files under ignored `data/raw/`.
- Abort on checksum mismatch, duplicate strict truth IDs, split leakage, invalid probabilities,
  a selected edge absent from candidates, or an incomplete component entering strict metrics.
- A network failure may be retried with the identical URL. Do not replace catalogs, sources,
  controls, or components after inspecting performance.
- Any deviation requires a dated amendment before rerunning and must preserve the original
  result as an invalidated artifact.
