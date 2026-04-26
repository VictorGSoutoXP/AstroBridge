#!/usr/bin/env python3
"""
setup_repo.py — Organiza o repositório AstroBridge.

Uso:
    python setup_repo.py

Funções:
    1. Move notebooks (01_*.ipynb, 02_*.ipynb) pra notebooks/
    2. Move dados (.csv, .parquet) pra data/processed/
    3. Move figuras (.png) pra reports/figures/
    4. Move PDF de relatório pra reports/
    5. Move test.py pra tests/
    6. Atualiza requirements.txt com lightkurve e ipykernel
    7. Atualiza pyproject.toml com novas dependências
    8. Atualiza README.md com badges e seção de validação
    9. Cria LICENSE MIT
    10. Cria CONTRIBUTING.md
    11. Cria .github/workflows/ci.yml (lint + smoke test)

Requisitos:
    - Python 3.10+
    - Executar a partir do root do repositório AstroBridge
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from textwrap import dedent
from datetime import datetime

# === EDITE ESTAS DUAS CONSTANTES SE QUISER OUTRO NOME/EMAIL NO LICENSE ===
AUTHOR_NAME = "Victor Gonçalves Souto"
AUTHOR_EMAIL = "victor@soutoconsultoria.com.br"
GITHUB_USER = "VictorGSoutoXP"
PROJECT_NAME = "AstroBridge"
# =========================================================================

REPO_ROOT = Path.cwd()
THIS_YEAR = datetime.now().year


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def colorize(text: str, color: str) -> str:
    """Adiciona cor ANSI ao texto (funciona em Linux/macOS e Windows 10+)."""
    codes = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{codes.get(color, '')}{text}{codes['reset']}"


def section(title: str) -> None:
    print()
    print(colorize("=" * 70, "blue"))
    print(colorize(f"  {title}", "bold"))
    print(colorize("=" * 70, "blue"))


def log_action(verb: str, src: str, dst: str | None = None) -> None:
    if dst:
        print(f"  {colorize('→', 'green')} {verb}: {src}  →  {dst}")
    else:
        print(f"  {colorize('→', 'green')} {verb}: {src}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst: Path) -> bool:
    """Move arquivo se existir e destino não existir. Retorna True se mexeu."""
    if not src.exists():
        return False
    if dst.exists():
        print(f"  {colorize('!', 'yellow')} pulando {src.name}: {dst} já existe")
        return False
    ensure_dir(dst.parent)
    shutil.move(str(src), str(dst))
    log_action("movido", str(src.relative_to(REPO_ROOT)),
               str(dst.relative_to(REPO_ROOT)))
    return True


# ----------------------------------------------------------------------------
# planejamento (lista o que vai fazer antes de fazer)
# ----------------------------------------------------------------------------
def plan_file_moves() -> list[tuple[Path, Path]]:
    """Lista todos os movimentos planejados."""
    moves: list[tuple[Path, Path]] = []

    # notebooks
    for nb in REPO_ROOT.glob("*.ipynb"):
        moves.append((nb, REPO_ROOT / "notebooks" / nb.name))

    # dados (csv, parquet) — mas NÃO mexer em requirements.txt
    for ext in ("*.csv", "*.parquet"):
        for f in REPO_ROOT.glob(ext):
            moves.append((f, REPO_ROOT / "data" / "processed" / f.name))

    # figuras
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.pdf"):
        for f in REPO_ROOT.glob(ext):
            # PDFs de relatório vão pra reports/, imagens pra reports/figures/
            if f.suffix.lower() == ".pdf":
                moves.append((f, REPO_ROOT / "reports" / f.name))
            else:
                moves.append((f, REPO_ROOT / "reports" / "figures" / f.name))

    # test.py órfão
    if (REPO_ROOT / "test.py").exists():
        moves.append((REPO_ROOT / "test.py",
                      REPO_ROOT / "tests" / "test_smoke.py"))

    return moves


# ----------------------------------------------------------------------------
# arquivos a serem criados/atualizados
# ----------------------------------------------------------------------------
REQUIREMENTS_TXT = dedent("""\
    # core
    pandas>=2.2,<3.0
    numpy>=1.26
    scipy>=1.12

    # astronomia
    astropy>=6.0
    astroquery>=0.4.7
    lightkurve>=2.6

    # ML / estatística
    scikit-learn>=1.4

    # I/O
    pyarrow>=15.0

    # utilidades
    matplotlib>=3.8
    tqdm>=4.66

    # ambiente jupyter
    ipykernel>=7.0
    jupyterlab>=4.0

    # dev (opcional, mas listado para reprodutibilidade)
    pytest>=8.0
    ruff>=0.6
""")


PYPROJECT_TOML = dedent(f"""\
    [project]
    name = "astrobridge"
    version = "0.1.0"
    description = "Probabilistic point-source cross-matching: Gaia DR3 × AllWISE × TESS with Budavári-Szalay Bayes factors and FLINT-α novelty detection."
    readme = "README.md"
    requires-python = ">=3.10"
    license = {{text = "MIT"}}
    authors = [
        {{name = "{AUTHOR_NAME}", email = "{AUTHOR_EMAIL}"}}
    ]
    keywords = ["astronomy", "cross-match", "gaia", "wise", "bayesian", "flint"]
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Astronomy",
    ]
    dependencies = [
        "pandas>=2.2,<3.0",
        "numpy>=1.26",
        "scipy>=1.12",
        "astropy>=6.0",
        "astroquery>=0.4.7",
        "lightkurve>=2.6",
        "scikit-learn>=1.4",
        "pyarrow>=15.0",
        "matplotlib>=3.8",
        "tqdm>=4.66",
    ]

    [project.optional-dependencies]
    dev = [
        "pytest>=8.0",
        "ruff>=0.6",
        "ipykernel>=7.0",
        "jupyterlab>=4.0",
    ]

    [project.urls]
    Repository = "https://github.com/{GITHUB_USER}/{PROJECT_NAME}"
    Issues = "https://github.com/{GITHUB_USER}/{PROJECT_NAME}/issues"

    [tool.setuptools]
    package-dir = {{"" = "src"}}

    [tool.setuptools.packages.find]
    where = ["src"]

    [tool.ruff]
    line-length = 100
    target-version = "py310"

    [tool.ruff.lint]
    select = ["E", "F", "W", "I", "N", "UP"]
    ignore = ["E501"]

    [tool.pytest.ini_options]
    pythonpath = ["src"]
    testpaths = ["tests"]
""")


def render_readme() -> str:
    return dedent(f"""\
        # AstroBridge

        ![Python](https://img.shields.io/badge/python-3.10%2B-blue)
        ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
        ![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

        Probabilistic point-source cross-matching across astronomical catalogs (Gaia DR3 × AllWISE × TESS), with Budavári–Szalay Bayes factors, Hungarian-algorithm uniqueness resolution, and a normalizing-flow novelty detection layer (FLINT-α, in development).

        > **Status (Apr 2026):** Working pipeline validated on NGC 2516. Currently developing the FLINT-α novelty channel via conditional normalizing flows.

        ---

        ## What this project does

        - Queries Gaia DR3, AllWISE, and the TESS Input Catalog over a sky region
        - Propagates Gaia DR3 (J2016.0) positions to the AllWISE epoch (J2010.5) using proper motions
        - Computes Bayes factors per Budavári & Szalay (2008, ApJ 679, 301) with heteroscedastic per-source uncertainties
        - Resolves match uniqueness via the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`)
        - Cross-matches the resulting catalog against SIMBAD for known-object labeling
        - Identifies cluster members via parallax + collective proper motion
        - Surfaces novelty candidates via Isolation Forest (baseline) → conditional normalizing flow (FLINT-α, planned)
        - Validates against the Cantat-Gaudin & Anders (2020) published cluster member catalog

        ## Validation

        Current pipeline performance on NGC 2516 (versus Cantat-Gaudin & Anders 2020):

        - **Cluster members identified:** ~427 candidates with parallax ∈ [2.0, 2.8] mas + |Δμ| < 2 mas/yr
        - **Reproducible CMD:** `reports/figures/cmd_ngc2516.png`
        - **Full validation report:** `reports/VALIDATION_REPORT.md` (auto-generated by notebook 02)

        See `notebooks/02_validacao_cantat_gaudin.ipynb` for the full validation workflow with precision/recall, ROC-AUC, ablation study, and confusion matrix analysis.

        ## Installation

        ```bash
        # Clone
        git clone https://github.com/{GITHUB_USER}/{PROJECT_NAME}.git
        cd {PROJECT_NAME}

        # Create virtual environment
        python -m venv .venv

        # Activate (Windows)
        .venv\\Scripts\\activate

        # Activate (macOS / Linux)
        source .venv/bin/activate

        # Install dependencies
        python -m pip install --upgrade pip
        pip install -r requirements.txt

        # Register Jupyter kernel
        python -m ipykernel install --user --name astrobridge \\
            --display-name "Python ({PROJECT_NAME})"
        ```

        ## Run the notebooks

        ```bash
        jupyter lab
        ```

        Then open in order:

        1. `notebooks/01_ngc2516_xmatch_v3.ipynb` — full cross-match pipeline + novelty surrogate
        2. `notebooks/02_validacao_cantat_gaudin.ipynb` — scientific validation against published catalog

        ## Project layout

        ```
        AstroBridge/
        ├── data/
        │   ├── raw/         # immutable downloaded catalogs
        │   ├── interim/     # intermediate processing
        │   └── processed/   # final cross-matched outputs (.parquet, .csv)
        ├── notebooks/       # exploratory and analysis notebooks
        ├── reports/
        │   └── figures/     # publication-ready plots
        ├── src/
        │   └── astrobridge/ # importable Python package
        ├── tests/           # pytest unit tests
        ├── .github/
        │   └── workflows/   # GitHub Actions CI
        ├── requirements.txt
        ├── pyproject.toml
        ├── LICENSE
        ├── CONTRIBUTING.md
        └── README.md
        ```

        ## Roadmap

        - [x] **Phase 1:** Working Bayesian cross-match pipeline on a single field (NGC 2516)
        - [x] **Phase 2:** Scientific validation against published reference catalog (Cantat-Gaudin & Anders 2020)
        - [ ] **Phase 3 (in progress):** FLINT-α — replace Isolation Forest with conditional normalizing flows for principled novelty detection
        - [ ] **Phase 4:** Reproduce NWAY (Salvato+ 2018) on XMM-COSMOS as published-benchmark comparison
        - [ ] **Phase 5:** Extend to multi-cluster pipeline (M67, Pleiades, Hyades) and write methods paper

        ## Key references

        - Budavári, T. & Szalay, A. S. (2008). *Probabilistic Cross-Identification of Astronomical Sources.* ApJ 679, 301.
        - Pineau, F.-X., et al. (2017). *Probabilistic multi-catalogue positional cross-match.* A&A 597, A89.
        - Salvato, M., et al. (2018). *Finding counterparts for all-sky X-ray surveys with NWAY.* MNRAS 473, 4937.
        - Cantat-Gaudin, T. & Anders, F. (2020). *Clusters and mirages.* A&A 633, A99.
        - Marrese, P. M., et al. (2019). *Gaia Data Release 2: Cross-match with external catalogues.* A&A 621, A144.

        ## License

        MIT License — see [LICENSE](LICENSE).

        ## Author

        {AUTHOR_NAME} ({AUTHOR_EMAIL}) — data engineer & statistics graduate student. Independent contributor.

        See [CONTRIBUTING.md](CONTRIBUTING.md) for collaboration interest.
    """)


def render_license() -> str:
    return dedent(f"""\
        MIT License

        Copyright (c) {THIS_YEAR} {AUTHOR_NAME}

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.
    """)


def render_contributing() -> str:
    return dedent(f"""\
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

        **{AUTHOR_NAME}** — {AUTHOR_EMAIL}

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
    """)


GITHUB_ACTIONS_CI = dedent("""\
    name: CI

    on:
      push:
        branches: [main]
      pull_request:
        branches: [main]

    jobs:
      lint-and-smoke-test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: ["3.11", "3.12"]

        steps:
          - uses: actions/checkout@v4

          - name: Set up Python ${{ matrix.python-version }}
            uses: actions/setup-python@v5
            with:
              python-version: ${{ matrix.python-version }}
              cache: pip

          - name: Install dependencies
            run: |
              python -m pip install --upgrade pip
              pip install ruff pytest
              pip install -r requirements.txt

          - name: Lint with ruff
            run: ruff check . --output-format=github
            continue-on-error: true  # warnings don't block; remove later when codebase is clean

          - name: Run smoke tests
            run: pytest tests/ -v --tb=short
""")


SMOKE_TEST = dedent('''\
    """Smoke test — verifica que dependências críticas importam.

    Não é teste de funcionalidade científica; só garante que o ambiente está sano
    e que CI vai passar. Testes científicos virão em fase posterior do projeto.
    """


    def test_core_imports():
        """Bibliotecas centrais devem importar sem erro."""
        import numpy
        import pandas
        import scipy
        import sklearn
        assert numpy.__version__
        assert pandas.__version__


    def test_astronomy_imports():
        """Stack de astronomia deve importar sem erro."""
        import astropy
        import astroquery
        assert astropy.__version__
        assert astroquery.__version__


    def test_lightkurve_import():
        """lightkurve deve importar (depende de muitas libs transitivas)."""
        import lightkurve
        assert lightkurve.__version__
''')


GITIGNORE_ADDITIONS = dedent("""\

    # AstroBridge-specific
    data/raw/*
    data/interim/*
    data/processed/*.parquet
    !data/raw/.gitkeep
    !data/interim/.gitkeep
    !data/processed/.gitkeep
    reports/figures/*.png
    reports/figures/*.jpg
    !reports/figures/.gitkeep
""")


# ----------------------------------------------------------------------------
# execução
# ----------------------------------------------------------------------------
def main() -> int:
    section(f"Setup do repositório {PROJECT_NAME}")
    print(f"Diretório atual: {REPO_ROOT}")
    print(f"Autor:           {AUTHOR_NAME} <{AUTHOR_EMAIL}>")
    print(f"GitHub:          @{GITHUB_USER}")

    # validação básica: estamos no lugar certo?
    sentinels = ["pyproject.toml", "requirements.txt", "README.md"]
    found = [s for s in sentinels if (REPO_ROOT / s).exists()]
    if len(found) < 2:
        print(colorize(
            "\n[ERRO] Este script deve ser executado a partir do root do repositório AstroBridge.\n"
            f"Esperava encontrar {sentinels}, achei só {found}.",
            "red"
        ))
        return 1

    # ------------------------------------------------------------------
    # planeja
    # ------------------------------------------------------------------
    section("Plano de execução")

    moves = plan_file_moves()
    print(f"\n[1] Arquivos a mover ({len(moves)}):")
    for src, dst in moves:
        print(f"    {src.relative_to(REPO_ROOT)} → {dst.relative_to(REPO_ROOT)}")
    if not moves:
        print("    (nenhum — repo já organizado)")

    files_to_create_or_update = [
        ("requirements.txt", "atualizar"),
        ("pyproject.toml", "atualizar"),
        ("README.md", "sobrescrever (backup em README.md.bak)"),
        ("LICENSE", "criar"),
        ("CONTRIBUTING.md", "criar"),
        (".github/workflows/ci.yml", "criar"),
        ("tests/test_smoke.py", "criar (se não existir)"),
        (".gitignore", "anexar entradas (se faltarem)"),
    ]
    print(f"\n[2] Arquivos a criar/atualizar ({len(files_to_create_or_update)}):")
    for fname, action in files_to_create_or_update:
        print(f"    {fname}  ({action})")

    print(f"\n[3] Diretórios a garantir:")
    for d in ["data/raw", "data/interim", "data/processed",
              "notebooks", "reports/figures",
              "src/astrobridge", "tests", ".github/workflows"]:
        print(f"    {d}/")

    # ------------------------------------------------------------------
    # confirmação
    # ------------------------------------------------------------------
    print()
    print(colorize("Atenção: este script vai modificar arquivos no disco.", "yellow"))
    print(colorize("Recomendado: 'git status' limpo antes de continuar, pra você poder reverter com 'git restore' se quiser.", "yellow"))
    print()
    answer = input(colorize("Continuar? [s/N] ", "bold")).strip().lower()
    if answer not in ("s", "sim", "y", "yes"):
        print(colorize("Abortado pelo usuário.", "red"))
        return 0

    # ------------------------------------------------------------------
    # executa
    # ------------------------------------------------------------------
    section("Executando")

    # 1. cria todos os diretórios
    print("\n[1/4] Criando estrutura de diretórios...")
    for d in ["data/raw", "data/interim", "data/processed",
              "notebooks", "reports/figures",
              "src/astrobridge", "tests", ".github/workflows"]:
        ensure_dir(REPO_ROOT / d)
        # adiciona .gitkeep em pastas que estarão vazias por causa do .gitignore
        if d.startswith("data/") or d == "reports/figures":
            gitkeep = REPO_ROOT / d / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()
                log_action("criado", str(gitkeep.relative_to(REPO_ROOT)))

    # garante __init__.py no pacote
    pkg_init = REPO_ROOT / "src" / "astrobridge" / "__init__.py"
    if not pkg_init.exists():
        pkg_init.write_text('"""AstroBridge package."""\n__version__ = "0.1.0"\n', encoding="utf-8")
        log_action("criado", str(pkg_init.relative_to(REPO_ROOT)))

    # 2. movimentações
    print("\n[2/4] Movendo arquivos...")
    moved_count = 0
    for src, dst in moves:
        if safe_move(src, dst):
            moved_count += 1
    if moved_count == 0:
        print(f"  {colorize('•', 'yellow')} nenhum arquivo movido")

    # 3. arquivos novos / atualizados
    print("\n[3/4] Criando/atualizando arquivos de configuração...")

    def write_file(rel_path: str, content: str, backup: bool = False) -> None:
        target = REPO_ROOT / rel_path
        ensure_dir(target.parent)
        if target.exists() and backup:
            bak = target.with_suffix(target.suffix + ".bak")
            shutil.copy(target, bak)
            log_action("backup", str(target.relative_to(REPO_ROOT)),
                       str(bak.relative_to(REPO_ROOT)))
        target.write_text(content, encoding="utf-8")
        log_action("escrito", str(target.relative_to(REPO_ROOT)))

    write_file("requirements.txt", REQUIREMENTS_TXT)
    write_file("pyproject.toml", PYPROJECT_TOML)
    write_file("README.md", render_readme(), backup=True)
    write_file("LICENSE", render_license())
    write_file("CONTRIBUTING.md", render_contributing())
    write_file(".github/workflows/ci.yml", GITHUB_ACTIONS_CI)

    # smoke test só se não existir (não sobrescreve trabalho do usuário)
    smoke_path = REPO_ROOT / "tests" / "test_smoke.py"
    if not smoke_path.exists():
        write_file("tests/test_smoke.py", SMOKE_TEST)
    else:
        print(f"  {colorize('!', 'yellow')} tests/test_smoke.py já existe — não sobrescrito")

    # 4. .gitignore — anexa só se as entradas não estiverem lá
    print("\n[4/4] Atualizando .gitignore...")
    gitignore = REPO_ROOT / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if "AstroBridge-specific" not in existing:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write(GITIGNORE_ADDITIONS)
        log_action("anexado", ".gitignore")
    else:
        print(f"  {colorize('•', 'yellow')} .gitignore já contém entradas AstroBridge — pulado")

    # ------------------------------------------------------------------
    # resumo
    # ------------------------------------------------------------------
    section("Concluído")
    print()
    print(colorize("Próximos passos manuais:", "bold"))
    print()
    print("  1. Inspecione as mudanças:")
    print("     git status")
    print("     git diff README.md")
    print()
    print("  2. Verifique que os notebooks ainda rodam (caminhos relativos podem precisar de ajuste):")
    print("     jupyter lab notebooks/01_ngc2516_xmatch_v3.ipynb")
    print()
    print("  3. Se notebook 02 quebrar pelo path do parquet, edite a variável `candidates_for_path`:")
    print("     ele já procura em ['data/processed/', 'root', '../data/processed/']")
    print()
    print("  4. Rode os testes localmente:")
    print("     pytest tests/")
    print()
    print("  5. Se tudo bem, comite:")
    print('     git add -A')
    print('     git commit -m "chore: organize repo structure, add LICENSE/CI/CONTRIBUTING"')
    print('     git push')
    print()
    print("  6. README.md.bak preserva sua versão anterior. Apague quando confortável:")
    print("     rm README.md.bak")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())