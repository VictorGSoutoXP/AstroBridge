from pathlib import Path


def test_membership_report_keeps_scope_warning():
    report = Path("reports/VALIDATION_REPORT.md").read_text(encoding="utf-8")
    assert "não valida se os pares" in report
    assert "O pipeline AstroBridge foi validado" not in report
    assert "always-member baseline" not in report
    assert "baseline que marca todas as fontes" in report


def test_readme_reports_failed_external_benchmark_without_nasa_claim():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "the frozen decision rule failed" in readme
    assert "must not be described as NASA-validated" in readme
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


def test_xmm_cosmos_report_preserves_failed_decision_and_scope():
    report = Path("reports/XMM_COSMOS_BENCHMARK_RESULTS.md").read_text(encoding="utf-8")
    assert "decision rule **failed**" in report
    assert "not an all-sky validation or a NASA-readiness claim" in report
    assert "shifted positions" in report
    assert "pseudo-negatives" in report
