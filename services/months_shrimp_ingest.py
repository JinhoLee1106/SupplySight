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

import argparse
import os

from dotenv import load_dotenv
load_dotenv()

from services.PostgresHelper import PostgresHelper
from services.combined_monthly_data import build_months_product_dataframe
from services.product_config import get_product_config


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


def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upsert a product-specific months table in Postgres.")
    p.add_argument(
        "--product",
        type=str,
        default="shrimp",
        help="Product to ingest. Supported: shrimp, salmon, tuna, whitefish.",
    )
    return p.parse_args()


def main(product: str = "shrimp") -> None:
    config = get_product_config(product)
    print(f"Building {config.months_table} rows from {config.name}_features + fao_{config.name}_price_index...")
    df = build_months_product_dataframe(config.name)

    records = df.to_dict(orient="records")
    if not records:
        print("No records to write; exiting.")
        return

    print(f"Upserting {len(records)} rows into {config.months_table}...")
    helper = get_helper()
    try:
        helper.update_table(config.months_table, records, primary_key="date")
    finally:
        helper.close()

    print("Done.")


if __name__ == "__main__":
    args = _cli()
    main(product=args.product)
