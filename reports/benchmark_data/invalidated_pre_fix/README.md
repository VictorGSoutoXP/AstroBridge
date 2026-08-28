# Invalidated pre-fix confirmatory outputs

These artifacts are retained only for audit provenance and must not be included in any
benchmark total. They were produced after the original internal protocol boundary `ca080e7`
and before a code review identified two implementation defects:

1. the finite-footprint prior odds omitted the `1/(4*pi)` normalization required when used
   with the analytic all-sky Budavári-Szalay Bayes factor; and
2. the one-to-one solver maximized products of binary probabilities instead of joint odds.

The North Galactic Pole, South Galactic Pole, and Galactic anticenter JSON/CSV pairs were
successful executions of the invalid implementation. Vela was interrupted after the audit
finding. The first Baade-window and Orion attempts ended with Gaia TAP HTTP 500 errors and
created no output. Every field is rerun from scratch after the corrective commit; only those
post-fix files are valid.
