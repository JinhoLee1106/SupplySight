#!/usr/bin/env python3
"""
services/months_shrimp_ingest.py

Upsert `months_shrimp` in Postgres.

Default: build the table-shaped frame in memory from processed CSVs:
  database/processed/shrimp_features.csv
  database/processed/fao_shrimp_price_index.csv
(see services/combined_monthly_data.build_months_shrimp_dataframe)

Optional: --from-csv PATH to load a legacy monthly_training_data.csv (MONTH column).

Environment variables for DB connection:
  POSTGRES_HOST
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_PORT (optional, default 5432)
  POSTGRES_DB   (optional, default "postgres")
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from services.PostgresHelper import PostgresHelper
from services.combined_monthly_data import (
    build_months_shrimp_dataframe,
    load_months_shrimp_from_legacy_csv,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "database" / "processed"


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
    parser = argparse.ArgumentParser(description="Upsert months_shrimp from merged monthly data.")
    parser.add_argument(
        "--from-csv",
        type=Path,
        default=None,
        help=(
            "Optional path to legacy monthly_training_data.csv (MONTH + metrics). "
            f"Default: build from shrimp_features + FAO under {PROCESSED}."
        ),
    )
    args = parser.parse_args()

    if args.from_csv is not None:
        print(f"Loading months_shrimp rows from {args.from_csv}...")
        df = load_months_shrimp_from_legacy_csv(args.from_csv)
    else:
        print("Building months_shrimp rows from shrimp_features + fao_shrimp_price_index...")
        df = build_months_shrimp_dataframe()

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
