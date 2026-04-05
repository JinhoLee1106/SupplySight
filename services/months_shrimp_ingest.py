#!/usr/bin/env python3
"""
services/months_shrimp_ingest.py

Upsert `months_shrimp` in Postgres.

Builds the table-shaped frame in memory from:
  database/processed/shrimp_features.csv
  database/processed/fao_shrimp_price_index.csv
(see services.combined_monthly_data.build_months_shrimp_dataframe)

Full pipeline (e.g. history 2013-01 through 2026-12):

1. Census: ``python -m services.census.ingest_shrimp --time-from 2013-01 --time-to 2026-12``
   (needs ``CENSUS_API_KEY``; optional env ``SHRIMP_TIME_FROM`` / ``SHRIMP_TIME_TO``).
2. Features: ``python -m services.census.feature_engineering``
3. Optional: refresh FAO price CSV: ``python -m services.price.ingest_fao_price_index``
4. This module: ``python -m services.months_shrimp_ingest``

Environment variables for DB connection:
  POSTGRES_HOST
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_PORT (optional, default 5432)
  POSTGRES_DB   (optional, default "postgres")
"""
from __future__ import annotations

import os

from services.PostgresHelper import PostgresHelper
from services.combined_monthly_data import build_months_shrimp_dataframe


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
