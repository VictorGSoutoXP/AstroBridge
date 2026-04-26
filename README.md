# AstroBridge

Pipeline inicial para cross-match astronômico entre Gaia DR3, AllWISE e SIMBAD.

## Objetivo

Construir uma base reproduzível para estudar associação probabilística entre catálogos astronômicos, começando com:

- consulta Gaia DR3;
- consulta AllWISE;
- correção de época/movimento próprio;
- cross-match por coordenada;
- consulta SIMBAD;
- cálculo de evidência posicional;
- exportação de resultados.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Rodar o pipeline

```bash
python -m astrobridge.pipeline --ra 83.633 --dec 22.0145 --radius 0.05 --out data/processed/astro_matches.csv
```

## Rodar com NGC 2516

```bash
python -m astrobridge.pipeline --ra 119.50 --dec -60.83 --radius 0.60 --out data/processed/ngc2516_matches.csv
```

## Estrutura

```text
AstroBridge/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
├── reports/
│   └── figures/
├── src/
│   └── astrobridge/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```
