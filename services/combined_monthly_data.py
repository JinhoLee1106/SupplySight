#!/usr/bin/env python3
"""
services/combined_monthly_data.py

Build a monthly training dataset combining:
- Census shrimp features (volume + engineered features)
- FAO shrimp price index

Output:
  database/processed/monthly_training_data.csv

One row per MONTH with columns like:
  MONTH,
  monthly_import,
  avg_unit_value_per_kg,
  avg_air_share,
  avg_container_ratio,
  monthly_import_mom_pct,
  monthly_import_yoy_pct,
  monthly_import_roll3_avg,
  monthly_import_roll6_avg,
  monthly_import_roll3_std,
  monthly_import_roll6_std,
  monthly_import_zscore_6,
  price_index_value
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "database" / "processed"

SHRIMP_FEATURES = PROCESSED / "shrimp_features.csv"
PRICE_INDEX = PROCESSED / "fao_shrimp_price_index.csv"
OUTPUT = PROCESSED / "monthly_training_data.csv"


def build_monthly_from_shrimp() -> pd.DataFrame:
    """Aggregate shrimp_features.csv to one row per MONTH."""
    if not SHRIMP_FEATURES.exists():
        raise FileNotFoundError(f"Missing shrimp features: {SHRIMP_FEATURES}")

    df = pd.read_csv(SHRIMP_FEATURES)

    # MONTH stored as YYYY-MM string
    df["MONTH"] = pd.to_datetime(df["MONTH"], format="%Y-%m")

    agg = {
        "total_weight_mo": "sum",          # monthly_import
        "unit_value_per_kg": "mean",       # avg_unit_value_per_kg
        "air_share": "mean",               # avg_air_share
        "container_ratio": "mean",         # avg_container_ratio
        "weight_mom_pct": "mean",
        "weight_yoy_pct": "mean",
        "weight_roll3_avg": "mean",
        "weight_roll6_avg": "mean",
        "weight_roll3_std": "mean",
        "weight_roll6_std": "mean",
        "weight_zscore_6": "mean",
    }

    # Only keep columns that actually exist
    agg = {col: func for col, func in agg.items() if col in df.columns}

    monthly = df.groupby("MONTH").agg(agg).reset_index()

    rename_map: dict[str, str] = {}
    if "total_weight_mo" in monthly.columns:
        rename_map["total_weight_mo"] = "monthly_import"
    if "weight_mom_pct" in monthly.columns:
        rename_map["weight_mom_pct"] = "monthly_import_mom_pct"
    if "weight_yoy_pct" in monthly.columns:
        rename_map["weight_yoy_pct"] = "monthly_import_yoy_pct"
    if "weight_roll3_avg" in monthly.columns:
        rename_map["weight_roll3_avg"] = "monthly_import_roll3_avg"
    if "weight_roll6_avg" in monthly.columns:
        rename_map["weight_roll6_avg"] = "monthly_import_roll6_avg"
    if "weight_roll3_std" in monthly.columns:
        rename_map["weight_roll3_std"] = "monthly_import_roll3_std"
    if "weight_roll6_std" in monthly.columns:
        rename_map["weight_roll6_std"] = "monthly_import_roll6_std"
    if "weight_zscore_6" in monthly.columns:
        rename_map["weight_zscore_6"] = "monthly_import_zscore_6"
    if "unit_value_per_kg" in monthly.columns:
        rename_map["unit_value_per_kg"] = "avg_unit_value_per_kg"
    if "air_share" in monthly.columns:
        rename_map["air_share"] = "avg_air_share"
    if "container_ratio" in monthly.columns:
        rename_map["container_ratio"] = "avg_container_ratio"

    monthly = monthly.rename(columns=rename_map)
    return monthly


def load_price_index() -> pd.DataFrame:
    """Load FAO shrimp price index and normalize columns."""
    if not PRICE_INDEX.exists():
        raise FileNotFoundError(f"Missing FAO price index: {PRICE_INDEX}")

    df = pd.read_csv(PRICE_INDEX)
    if "date" not in df.columns or "value" not in df.columns:
        raise ValueError(
            f"Expected 'date' and 'value' columns in {PRICE_INDEX}, got {list(df.columns)}"
        )

    df["MONTH"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"value": "price_index_value"})

    # If there are multiple rows per month (e.g. multiple commodities), average them
    df = df.groupby("MONTH", as_index=False)["price_index_value"].mean()

    return df[["MONTH", "price_index_value"]]


def main() -> None:
    print("Building monthly training data from shrimp features and FAO price index...")

    monthly_imports = build_monthly_from_shrimp()
    price = load_price_index()

    combined = monthly_imports.merge(price, on="MONTH", how="left")
    combined = combined.sort_values("MONTH").reset_index(drop=True)

    # Format MONTH as YYYY-MM for output
    combined["MONTH"] = combined["MONTH"].dt.strftime("%Y-%m")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT, index=False)

    print(f"Wrote {len(combined)} rows to {OUTPUT}")
    print("Columns:", list(combined.columns))


if __name__ == "__main__":
    main()

