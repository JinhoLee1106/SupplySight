#!/usr/bin/env python3
"""
services/months_shrimp_ingest.py

Load the engineered monthly training data CSV and upsert it into the
`months_shrimp` Postgres table, so the DB mirrors the features that the
model uses.

Expected input CSV (produced by services/combined_monthly_data.py):
  database/processed/monthly_training_data.csv
with columns:
  MONTH (YYYY-MM),
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

Environment variables for DB connection:
  POSTGRES_HOST
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_PORT (optional, default 5432)
  POSTGRES_DB   (optional, default "postgres")
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from services.PostgresHelper import PostgresHelper

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "database" / "processed"
MONTHLY_CSV = PROCESSED / "monthly_training_data.csv"


def load_monthly() -> pd.DataFrame:
    if not MONTHLY_CSV.exists():
        raise FileNotFoundError(f"Missing monthly training data CSV: {MONTHLY_CSV}")

    df = pd.read_csv(MONTHLY_CSV)
    if "MONTH" not in df.columns:
        raise ValueError(f"'MONTH' column not found in {MONTHLY_CSV}")

    # Convert MONTH (YYYY-MM) to a proper timestamp, use first day of month
    df["MONTH"] = pd.to_datetime(df["MONTH"], format="%Y-%m")
    df["date"] = df["MONTH"].dt.to_period("M").dt.to_timestamp()

    # Reorder/select columns to match months_shrimp schema
    expected_cols = [
        "date",
        "monthly_import",
        "avg_unit_value_per_kg",
        "avg_air_share",
        "avg_container_ratio",
        "monthly_import_mom_pct",
        "monthly_import_yoy_pct",
        "monthly_import_roll3_avg",
        "monthly_import_roll6_avg",
        "monthly_import_roll3_std",
        "monthly_import_roll6_std",
        "monthly_import_zscore_6",
        "price_index_value",
    ]

    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in {MONTHLY_CSV}: {missing}")

    return df[expected_cols]


def get_helper() -> PostgresHelper:
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("POSTGRES_DB", "postgres")

    if not host or not user or not password:
        raise ValueError(
            "POSTGRES_HOST, POSTGRES_USER, and POSTGRES_PASSWORD must be set in the environment."
        )

    return PostgresHelper(host=host, user=user, password=password, port=port, dbname=dbname)


def main() -> None:
    print("Loading monthly_training_data.csv...")
    df = load_monthly()
    records = df.to_dict(orient="records")
    if not records:
        print("No records to write; exiting.")
        return

    print(f"Upserting {len(records)} rows into months_shrimp...")
    helper = get_helper()
    try:
        helper.update_table("months_shrimp", records, primary_key="date")
    finally:
        helper.close()

    print("Done.")


if __name__ == "__main__":
    main()

