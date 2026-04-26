from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def plot_cmd(matches: pd.DataFrame, output_path: str | Path) -> None:
    df = matches.copy()
    df = df.dropna(subset=["gaia_bp_rp", "gaia_phot_g_mean_mag"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 10))
    plt.scatter(df["gaia_bp_rp"], df["gaia_phot_g_mean_mag"], s=8, alpha=0.6)
    plt.gca().invert_yaxis()
    plt.xlabel("BP - RP")
    plt.ylabel("G")
    plt.title("Gaia CMD")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_distance_distribution(matches: pd.DataFrame, output_path: str | Path) -> None:
    df = matches.dropna(subset=["distance_arcsec"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.hist(df["distance_arcsec"], bins=30)
    plt.xlabel("Distância angular (arcsec)")
    plt.ylabel("Quantidade")
    plt.title("Distribuição de distância angular")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
