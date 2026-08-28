# Gaia DR3-AllWISE reference agreement study

**Query date:** 2026-08-27
**Status:** invalidated historical exploratory run; retained only for audit provenance.

> **Do not cite the numerical results below as evidence.** The implementation used for this
> run omitted the `1/(4*pi)` normalization required when combining the finite-footprint prior
> with the analytic all-sky Bayes factor. Its one-to-one solver also optimized products of
> binary probabilities rather than joint odds. Both defects were corrected in `b5f74ca`, and
> the valid held-out result is reported in
> `reports/GAIA_ALLWISE_CONFIRMATORY_RESULTS.md`.

This study compares AstroBridge with the official Gaia DR3-AllWISE best-neighbour table. The
official solution is a strong comparator because it uses the full Gaia five-parameter
covariance when available, external-catalog positional errors, local density, and all good
neighbours. It is not independent truth: both methods use Gaia and AllWISE positions, and the
official solution explicitly trades completeness against correctness.

## Preprocessing and comparison subset

1. Query Gaia DR3 inside the stated field.
2. Retain Gaia rows with both proper-motion components.
3. Query AllWISE in a cone expanded by the 2 arcsec candidate radius to avoid edge truncation.
4. Propagate Gaia positions from J2016.0 to the nominal AllWISE epoch J2010.5.
5. Run AstroBridge with candidate radius 2 arcsec, minimum posterior 0.5, and expected match
   fraction 0.7.
6. Fetch official best neighbours for exactly the retained Gaia source identifiers.
7. Define the least ambiguous official subset as `xm_flag == 8`, one official neighbour, and
   zero Gaia mates. Flag 8 denotes a five-parameter Gaia solution without the duplicate,
   resolved-source, or special-treatment flags.

The metrics below are therefore **agreement**, **candidate coverage**, and **not selected**.
They must not be renamed precision, recall, or accuracy.

## Historical exploratory fields (invalidated)

| Field | Center (deg) | Radius | Gaia | AllWISE | Clean official | Official in candidates | Agreements | Different selection | Not selected | Extra selections outside clean subset |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NGC 2516 | 119.5000, -60.8300 | 0.05 | 230 | 105 | 41 | 41 | 39 | 0 | 2 | 0 |
| COSMOS | 150.1163, 2.2058 | 0.05 | 33 | 130 | 26 | 26 | 26 | 0 | 0 | 1 |
| Cygnus plane | 305.0000, 40.0000 | 0.03 | 190 | 48 | 27 | 27 | 27 | 0 | 0 | 1 |
| Pleiades | 56.7500, 24.1167 | 0.05 | 76 | 159 | 43 | 43 | 43 | 0 | 0 | 0 |
| Barnard field | 269.4521, 4.6934 | 0.02 | 92 | 26 | 20 | 20 | 19 | 0 | 1 | 0 |
| Proxima field | 217.4292, -62.6795 | 0.02 | 424 | 24 | 6 | 6 | 5 | 0 | 1 | 0 |
| **Total** | — | — | **1,045** | **492** | **163** | **163** | **159** | **0** | **4** | **2** |

The clean-reference candidate coverage was 163/163 (100%). AstroBridge selected the same
counterpart for 159/163 (97.5%) and selected no different counterpart in this subset. Four
official candidates were not selected because their AstroBridge posterior was below 0.5. The
four posteriors were approximately 0.179, 0.315, 0.299, and 0.136; their official counterparts
were present in the candidate set.

The two extra selections occurred for Gaia sources outside the deliberately strict clean
official subset. They are not labeled false positives because the reference subset excludes
ambiguous and specially treated associations by design.

## Historical exploratory sensitivity grid (invalidated)

A grid over minimum posterior `{0.1, 0.2, 0.3, 0.5, 0.7, 0.9}` and expected match fraction
`{0.3, 0.7, 0.9}` was run on NGC 2516, COSMOS, Cygnus, and the Proxima field. These four fields
contained 100 clean official associations.

| Expected match fraction | Minimum posterior | Agreements | Different selection | Not selected | Agreement rate |
|---:|---:|---:|---:|---:|---:|
| 0.3 | 0.1 | 98 | 0 | 2 | 0.98 |
| 0.3 | 0.5 | 96 | 0 | 4 | 0.96 |
| 0.3 | 0.9 | 92 | 0 | 8 | 0.92 |
| 0.7 | 0.1 | 100 | 0 | 0 | 1.00 |
| 0.7 | 0.5 | 97 | 0 | 3 | 0.97 |
| 0.7 | 0.9 | 94 | 0 | 6 | 0.94 |
| 0.9 | 0.1 | 100 | 0 | 0 | 1.00 |
| 0.9 | 0.5 | 97 | 0 | 3 | 0.97 |
| 0.9 | 0.9 | 94 | 0 | 6 | 0.94 |

Lowering the threshold to 0.1 recovered every clean official association in these four fields
without a different selection. This is a hypothesis-generating result, not a calibrated
threshold: the fields were inspected while constructing the benchmark, so reusing them to
choose and evaluate 0.1 would leak test information.

## High-proper-motion limitation

The Gaia source corresponding to Proxima has total proper motion of about 3,859 mas/yr in the
queried field, but it has no entry in the official Gaia DR3-AllWISE best-neighbour table used
here. Consequently, this comparator cannot establish performance for that extreme-motion
case. A dedicated independently established reference or direct image/catalog inspection is
required for high-proper-motion validation.

## Reproduce

```bash
astrobridge-reference-validate \
  --ra 119.5 \
  --dec -60.83 \
  --radius 0.05 \
  --candidate-radius-arcsec 2.0 \
  --min-posterior 0.5 \
  --expected-match-fraction 0.7 \
  --output data/processed/ngc2516_reference.json \
  --details-output data/processed/ngc2516_reference_details.csv
```

For the sensitivity grid, add:

```bash
--posterior-grid 0.1 0.2 0.3 0.5 0.7 0.9 \
--expected-fraction-grid 0.3 0.7 0.9
```

The JSON output records its UTC artifact-generation time, package version, configuration,
reference DOI, row count, and SHA-256 hashes of the Gaia and AllWISE identifier manifests.

## Resolution

The prospectively specified field study was rerun from scratch after the corrective boundary.
It achieved complete candidate coverage but failed its primary agreement decision rule. See
`reports/GAIA_ALLWISE_CONFIRMATORY_RESULTS.md`. A published benchmark with independently
established, high-confidence counterparts remains required; NWAY/XMM-COSMOS must not be called
ground truth without auditing how its reference labels were established.

## Sources

- [Gaia DR3 `allwise_best_neighbour` documentation](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_cross-matches/ssec_dm_allwise_best_neighbour.html)
- [Gaia DR3 `allwise_neighbourhood` documentation](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_cross-matches/ssec_dm_allwise_neighbourhood.html)
- [Gaia DR3 AllWISE best-neighbour DOI](https://doi.org/10.17876/gaia/dr.3/29)
- [Salvato et al. (2018), NWAY](https://arxiv.org/abs/1705.10711)
