# Contributing to AstroBridge

Thanks for considering contributing! AstroBridge is an early-stage research project
developed by an independent contributor. Collaboration is welcome, especially from
astronomers, statisticians, and ML researchers interested in probabilistic
cross-matching and novelty detection in astronomical surveys.

## How to collaborate

### Reporting issues

If you find a bug, an inconsistency in the methodology, or a reference that should
be cited, open an issue on GitHub describing:

- What you expected
- What you got
- Minimal reproducible example (if a bug)
- Relevant references (if a methodological point)

### Proposing changes

For small fixes (typos, small bugs, missing references), open a pull request directly.
For larger changes (new pipeline stages, new validation benchmarks, methodological
rewrites), please open an issue first to discuss the approach.

### Style

- Code is formatted with `ruff` (`ruff format` and `ruff check`).
- Notebooks should include narrative markdown cells explaining what each section does.
- All references to published methods should be cited inline (paper + year + journal).

## Reaching out for academic collaboration

If you are an astronomer, astrostatistician, or ML researcher interested in
co-authoring or extending this work — particularly the FLINT-α normalizing-flow
component or the streaming application to LSST alerts — please email:

**Victor Gonçalves Souto** — victor@soutoconsultoria.com.br

Include in your email:
- Brief description of your interest and relevant background
- Specific aspect of the project you would like to discuss
- Whether you have computational resources or access to data we could leverage

## Development setup

See `README.md` for installation. For development, also install dev dependencies:

```bash
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/
```

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.
