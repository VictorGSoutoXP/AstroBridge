from pathlib import Path


def test_membership_report_keeps_scope_warning():
    report = Path("reports/VALIDATION_REPORT.md").read_text(encoding="utf-8")
    assert "não valida se os pares" in report
    assert "O pipeline AstroBridge foi validado" not in report
    assert "always-member baseline" not in report
    assert "baseline que marca todas as fontes" in report


def test_readme_does_not_claim_external_validation():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Independent real-sky association validation is still pending" in readme
    assert "Working pipeline validated" not in readme


def test_legacy_notebook_cannot_overwrite_corrected_report():
    notebook = Path("notebooks/02_validacao_cantat_gaudin.ipynb").read_text(encoding="utf-8")
    assert "open('../reports/VALIDATION_REPORT.md', 'w'" not in notebook
    assert "O pipeline AstroBridge foi validado" not in notebook


def test_nasa_documents_do_not_claim_submission_readiness():
    path = Path("docs/NASA_SUBMISSION_PATH.md").read_text(encoding="utf-8")
    concept = Path("docs/NASA_CONCEPT_NOTE.md").read_text(encoding="utf-8")
    assert "no NASA program element has been selected" in path
    assert "not a NASA proposal" in concept
    assert "Not selected" in concept
