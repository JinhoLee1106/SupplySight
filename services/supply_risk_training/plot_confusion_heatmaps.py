#!/usr/bin/env python3
"""Render confusion-matrix heatmaps from exported CSV counts."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def draw_heatmap(tp: int, fp: int, tn: int, fn: int, title: str, out_path: Path) -> None:
    # Rows: Actual [Positive, Negative], Cols: Predicted [Positive, Negative]
    mat = np.array([[tp, fn], [fp, tn]], dtype=float)

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(mat, cmap="Blues")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks([0, 1], labels=["Pred +", "Pred -"])
    ax.set_yticks([0, 1], labels=["Actual +", "Actual -"])
    ax.set_title(title)

    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{int(mat[i, j])}", ha="center", va="center", color="black", fontsize=12)

    ax.set_xlabel("Prediction")
    ax.set_ylabel("Ground Truth")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    model_dir = Path("models")

    daily = pd.read_csv(model_dir / "confusion_daily_counts.csv").iloc[0]
    monthly = pd.read_csv(model_dir / "confusion_monthly_counts.csv").iloc[0]

    draw_heatmap(
        int(daily["tp"]),
        int(daily["fp"]),
        int(daily["tn"]),
        int(daily["fn"]),
        "Daily Confusion Matrix (threshold > 60)",
        model_dir / "confusion_matrix_daily.png",
    )

    draw_heatmap(
        int(monthly["tp"]),
        int(monthly["fp"]),
        int(monthly["tn"]),
        int(monthly["fn"]),
        "Monthly Confusion Matrix (threshold > 60)",
        model_dir / "confusion_matrix_monthly.png",
    )

    print("Wrote models/confusion_matrix_daily.png")
    print("Wrote models/confusion_matrix_monthly.png")


if __name__ == "__main__":
    main()
