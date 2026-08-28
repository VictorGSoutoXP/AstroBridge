# NASA-readiness checklist

This document is a project quality checklist. It does not imply NASA review, endorsement,
affiliation, or funding.

## Scientific validity

- [x] Separate association validation from downstream cluster-membership validation.
- [x] Include a deterministic benchmark with known true associations.
- [x] Report failure under increasing source density.
- [x] Run an internally specified held-out Gaia-AllWISE field comparison, invalidate the three
  pre-fix executions, rerun all fields from the corrected boundary, and report the failed
  primary decision rule.
- [ ] Validate against a published benchmark with independently established,
  high-confidence counterparts, such as an audited NWAY/XMM-COSMOS dataset.
- [ ] Add a reliable negative/control class and ambiguous-neighbour strata.
- [ ] Report results by magnitude, density, separation, proper motion, and quality flag.
- [ ] Propagate the full Gaia astrometric covariance matrix.
- [ ] Replace the single nominal AllWISE epoch with per-source observation epochs where
  available.
- [ ] Calibrate posterior probabilities with reliability curves, Brier score, and expected
  calibration error.
- [ ] Quantify sensitivity to candidate radius, prior odds, and unmatched threshold.

## Reproducibility

- [x] Keep deterministic unit and synthetic tests offline.
- [x] Make lint failures block continuous integration.
- [x] Provide command-line entry points for the pipeline and synthetic validation.
- [x] Record code commit, tracked-file state, dependency versions, query text,
  artifact-generation timestamp, effective prior, retry count, and content hashes for the
  held-out field run.
- [ ] Pin a complete computational environment and record operating-system details.
- [ ] Archive immutable input manifests, query text, retrieval timestamps, and checksums.
- [x] Execute and aggregate the real-sky field workflow without hidden notebook state.
- [x] Publish the field tables and machine-readable aggregate needed to verify current claims.

## Open science and governance

- [x] Use an open-source license.
- [x] Provide citation metadata, contribution guidance, and a code of conduct.
- [ ] Publish a versioned release and archive it in Zenodo or another repository that issues
  a persistent DOI.
- [ ] Add the release DOI to `CITATION.cff` and the README.
- [ ] Prepare an Open Science and Data Management Plan for the selected solicitation.

## Proposal preparation

- [ ] Identify a currently open and eligible NASA solicitation in NSPIRES.
- [ ] Confirm institutional and international-participation eligibility from the exact call.
- [ ] Map each scientific objective to a NASA mission-data return or program objective.
- [ ] Prepare a methods paper or preprint with independently reviewed results.
- [ ] Obtain domain review from an astronomer experienced in catalog cross-identification.

The current route assessment and eligibility constraints are documented in
[`NASA_SUBMISSION_PATH.md`](NASA_SUBMISSION_PATH.md). An internal, unsubmitted scientific draft
is in [`NASA_CONCEPT_NOTE.md`](NASA_CONCEPT_NOTE.md); its solicitation-mapping fields
must remain blank until a live, eligible program element is selected.

Official starting points:

- NASA Science funding opportunities: https://science.nasa.gov/researchers/sara/grant-solicitations/
- NSPIRES: https://nspires.nasaprs.com/
- NASA Science Information Policy: https://science.nasa.gov/researchers/science-information-policy/
