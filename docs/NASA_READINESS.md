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
- [x] Run a prospectively specified XMM-COSMOS--IRAC benchmark against Chandra-anchored,
  high-confidence counterparts and report its failed primary decision rule.
- [x] Add shifted pseudo-negative controls and set-valued ambiguous-neighbour strata, while
  keeping their evidentiary limitations explicit.
- [ ] Add independently established real unmatched cases; shifted controls are not proof of
  physical absence.
- [x] Report XMM-COSMOS results by candidate density, separation, and XMM positional error.
- [ ] Extend held-out strata to magnitude, proper motion, and catalog quality flags.
- [ ] Propagate the full Gaia astrometric covariance matrix.
- [ ] Replace the single nominal AllWISE epoch with per-source observation epochs where
  available.
- [x] Measure conditional pair-score reliability, Brier score, log loss, ECE, and an
  intercept-only calibration on a frozen split.
- [ ] Implement and validate normalized source-level probabilities over candidates plus
  `no counterpart`; pairwise calibration did not control shifted-source selections.
- [ ] Quantify sensitivity to candidate radius, prior odds, and unmatched threshold.

## Reproducibility

- [x] Keep deterministic unit and synthetic tests offline.
- [x] Make lint failures block continuous integration.
- [x] Provide command-line entry points for the pipeline and synthetic validation.
- [x] Record code commit, tracked-file state, dependency versions, query text,
  artifact-generation timestamp, effective prior, retry count, and content hashes for the
  held-out field run.
- [x] Record the operating system, Python and package versions, input/output hashes, source
  URLs, schemas, file times, code commit, and run times for XMM-COSMOS.
- [ ] Pin a complete computational environment rather than version ranges alone.
- [x] Commit the XMM-COSMOS input manifest, derived tables, metrics, and output checksums;
  third-party raw FITS files remain checksum-addressed downloads.
- [x] Execute and aggregate the real-sky field workflow without hidden notebook state.
- [x] Publish the field tables and machine-readable aggregate needed to verify current claims.
- [x] Reproduce every XMM-COSMOS scientific artifact byte for byte in a second clean run.

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
