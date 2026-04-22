#!/usr/bin/env python3
"""Plot validation lines from models/validation_backtest_monthly_table.txt."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

in_path = Path("models/validation_backtest_monthly_table.txt")
out_path = Path("models/validation_backtest_from_table.png")

rows = []
for line in in_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("Wrote") or line.startswith("label_ym"):
        continue
    parts = line.split()
    if len(parts) == 3:
        ym, y_true, y_pred = parts
        rows.append((ym, float(y_true), float(y_pred)))

df = pd.DataFrame(rows, columns=["label_ym", "y_true", "y_pred"])

plt.figure(figsize=(11, 5))
plt.plot(df["label_ym"], df["y_true"], marker="o", linewidth=2, label="Actual (y_true)")
plt.plot(
    df["label_ym"],
    df["y_pred"],
    marker="o",
    linewidth=2,
    linestyle="--",
    label="Predicted (y_pred)",
)
plt.title("Validation Backtest from Saved Table")
plt.xlabel("label_ym")
plt.ylabel("Risk score")
plt.ylim(0, 100)
plt.xticks(rotation=45, ha="right")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(out_path, dpi=180)

print(f"Wrote {out_path}")
print(df.to_string(index=False))
