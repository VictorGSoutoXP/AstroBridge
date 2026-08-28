# AstroBridge NASA concept note

**Status:** internal research draft; not a NASA proposal, not externally validated, and not
mapped to a live program element.

## Working title

Calibrated probabilistic cross-identification for reproducible multi-mission astronomical
catalog science

## Draft summary

Modern archival studies combine detections from surveys with different angular resolution,
epochs, selection functions, and source densities. Incorrect associations can propagate into
target selection, population inference, and anomaly rankings while still producing plausible
downstream plots. AstroBridge will develop and externally validate a transparent probabilistic
cross-identification workflow that propagates astrometric uncertainty and proper motion,
scores every local candidate, resolves one-to-one ambiguity, and reports calibrated match
probabilities. The research will benchmark against published, independently established
high-confidence references and held-out sky fields, quantify performance across density,
magnitude, separation, and quality
regimes, and release reproducible query manifests, software, tables, and calibration products
under an archival DOI. A later mission-specific work package may evaluate how calibrated
Gaia/infrared associations improve use of public TESS targets and light curves, but that claim
is outside the current package and requires a solicitation whose scope explicitly supports it.

## Scientific question

How reliably can positional evidence, epoch propagation, catalog density, and explicit
one-to-one ambiguity resolution identify cross-survey counterparts, and where is additional
photometric or mission-specific evidence required?

## Proposed objectives

1. **External validation:** reproduce at least one published cross-identification benchmark
   with known or high-confidence counterparts.
2. **Calibration and failure mapping:** measure precision, recall, reliability, Brier score,
   and expected calibration error by density, magnitude, separation, proper motion, and
   catalog quality.
3. **Astrometric model:** incorporate the full Gaia covariance and document approximations for
   surveys with incomplete uncertainty metadata.
4. **Reproducible release:** archive code, immutable input manifests, query text and times,
   checksums, derived tables, and figures under a versioned DOI.
5. **Mission relevance:** only after calibration, test a narrowly defined NASA mission-data
   use case selected from the exact solicitation.

## Falsifiable success criteria

- Pre-register benchmark splits, thresholds, and primary metrics before examining final test
  results.
- Compare against nearest-neighbor, fixed-radius, and always-match/unmatched baselines.
- Report confidence intervals and all failed or excluded cases.
- Demonstrate calibrated probabilities on held-out fields rather than only high F1 on a
  selected sample.
- Reproduce the principal tables from a clean environment using archived inputs.

## Expected open products

- tested Python package and command-line tools;
- external-benchmark and held-out-field result tables;
- calibration and sensitivity figures;
- machine-readable query and input manifests with checksums;
- methods manuscript or preprint; and
- immutable software/data archive with DOI.

## Required partners

- astronomer experienced in survey catalogs and cross-identification;
- statistician or astrostatistician for probability calibration and evaluation design;
- eligible submitting institution and AOR if the selected NASA opportunity requires a U.S.
  organization; and
- mission/archive specialist for any TESS or other NASA-specific work package.

## Solicitation mapping — deliberately blank

| Required field | Value |
|---|---|
| Solicitation and amendment | Not selected |
| Program element | Not selected |
| Program objective supported | Not established |
| Due date | Not established |
| PI and submitting organization | Not established |
| Foreign-participation determination | Not established |
| NASA mission/archive deliverable | Not established |

The concept must not be expanded into a full proposal until the go/no-go gates in
[`NASA_SUBMISSION_PATH.md`](NASA_SUBMISSION_PATH.md) are satisfied.
