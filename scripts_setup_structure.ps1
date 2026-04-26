$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path ".github/workflows" | Out-Null
New-Item -ItemType Directory -Force -Path "data/raw" | Out-Null
New-Item -ItemType Directory -Force -Path "data/interim" | Out-Null
New-Item -ItemType Directory -Force -Path "data/processed" | Out-Null
New-Item -ItemType Directory -Force -Path "notebooks" | Out-Null
New-Item -ItemType Directory -Force -Path "reports/figures" | Out-Null
New-Item -ItemType Directory -Force -Path "src/astrobridge" | Out-Null
New-Item -ItemType Directory -Force -Path "tests" | Out-Null

New-Item -ItemType File -Force -Path "data/raw/.gitkeep" | Out-Null
New-Item -ItemType File -Force -Path "data/interim/.gitkeep" | Out-Null
New-Item -ItemType File -Force -Path "data/processed/.gitkeep" | Out-Null
New-Item -ItemType File -Force -Path "reports/figures/.gitkeep" | Out-Null

Write-Host "Estrutura criada com sucesso."
