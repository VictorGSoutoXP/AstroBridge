# Confirmatory Gaia DR3-AllWISE agreement protocol

**Status:** frozen before querying the confirmatory fields. The Git commit first containing
this document is the registration boundary.

## Purpose

Confirm whether the exploratory Gaia DR3-AllWISE agreement pattern generalizes to new sky
fields without selecting thresholds after seeing their outcomes. This remains an
external-algorithm comparison, not ground-truth validation.

The six exploratory fields in `reports/GAIA_ALLWISE_REFERENCE_BENCHMARK.md` are excluded from
all confirmatory totals.

## Frozen primary configuration

- Gaia cone: field-specific radius below.
- AllWISE cone: Gaia radius plus 2 arcsec.
- Gaia epoch propagation: J2016.0 to nominal J2010.5.
- Gaia inclusion: both proper-motion components available.
- Candidate radius: 2.0 arcsec.
- Expected match fraction: 0.7.
- Minimum posterior: 0.5.
- Gaia query limit: 5,000 rows per field.
- Official clean subset: `xm_flag == 8`, `number_of_neighbours == 1`, and
  `number_of_mates == 0`.

The threshold 0.5 is primary because it was the project configuration before the exploratory
grid. Threshold 0.1 is a declared secondary analysis because it recovered additional official
associations in the exploratory fields. It must not replace the primary result.

## Confirmatory fields

The coordinates were chosen for astrophysical regime coverage, before retrieving their
AstroBridge or official cross-match outcomes.

| Field | RA (deg) | Dec (deg) | Radius (deg) | Intended regime |
|---|---:|---:|---:|---|
| North Galactic Pole | 192.8595 | 27.1283 | 0.05 | very low stellar density |
| South Galactic Pole | 12.8595 | -27.1283 | 0.05 | very low stellar density |
| Galactic anticenter | 86.4050 | 28.9360 | 0.03 | Galactic plane |
| Vela plane | 128.8360 | -45.1760 | 0.03 | Galactic plane |
| Baade window | 270.9000 | -30.0000 | 0.02 | crowded bulge window |
| Orion nebula | 83.8220 | -5.3910 | 0.03 | nebulosity and crowding |
| LMC field | 80.8940 | -69.7560 | 0.03 | external galaxy field |
| M31 field | 10.6847 | 41.2690 | 0.05 | external galaxy field |
| Hyades | 66.7500 | 15.8700 | 0.05 | nearby moving cluster |
| M4 | 245.8968 | -26.5258 | 0.03 | crowded globular cluster |

## Primary outcomes

Report field-level and aggregate counts for:

1. clean official associations;
2. clean official associations present in the AstroBridge candidate set;
3. same-counterpart selections;
4. different-counterpart selections;
5. official candidates present but not selected; and
6. AstroBridge selections outside the clean official subset.

Primary rates are candidate coverage and same-counterpart agreement divided by clean official
associations. Report Wilson 95% intervals for the aggregate proportions. Do not call these
precision, recall, or accuracy.

## Secondary analysis

Repeat only the selection step at minimum posterior 0.1 with expected match fraction 0.7. Do
not explore additional thresholds or priors on the confirmatory fields in this phase.

## Exclusions and failure handling

- A field with zero clean official associations remains in the report and is not replaced.
- A field reaching 5,000 Gaia rows is marked truncated and excluded from aggregate inference;
  its descriptive result may be shown separately.
- Service failures may be retried with the identical query. Record the failure and retry count.
- Do not remove individual sources after inspecting agreement status.
- Preserve the configuration, UTC time, package version, identifier hashes, and detailed
  comparison output for every successful query.

## Decision rule

This small confirmatory study succeeds as an engineering comparator if:

- aggregate candidate coverage is at least 0.95;
- the lower bound of the Wilson 95% interval for primary same-counterpart agreement is at
  least 0.90; and
- every different-counterpart selection is inspected and reported.

Passing this rule does not satisfy the external-truth requirement. The independent
NWAY/XMM-COSMOS or equivalent truth benchmark remains mandatory.
