#!/usr/bin/env python3
"""
services/supply_risk_training/supply_risk_db.py

Postgres helpers for supply risk ML.

Uses POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, optional POSTGRES_DB (default
postgres), POSTGRES_PORT (default 5432), POSTGRES_SSLMODE (default require; empty to disable).
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect() -> Any:
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    dbname = os.getenv("POSTGRES_DB", "postgres")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    sslmode_raw = os.getenv("POSTGRES_SSLMODE", "require")

    if not host or not user or not password:
        raise ValueError(
            "Set POSTGRES_HOST, POSTGRES_USER, and POSTGRES_PASSWORD (e.g. in .env)."
        )

    kwargs: dict[str, Any] = {
        "host": host,
        "user": user,
        "password": password,
        "dbname": dbname,
        "port": port,
        "connect_timeout": 15,
    }
    if sslmode_raw:
        kwargs["sslmode"] = sslmode_raw

    return psycopg2.connect(**kwargs)


def fetch_dates_shrimp(
    conn: Any,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """Load dates_shrimp rows; optional inclusive date bounds (YYYY-MM-DD)."""
    if date_from is None and date_to is None:
        q = "SELECT * FROM dates_shrimp ORDER BY date"
        return pd.read_sql_query(q, conn)
    q = "SELECT * FROM dates_shrimp WHERE TRUE"
    params: list[Any] = []
    if date_from is not None:
        q += " AND date >= %s"
        params.append(date_from)
    if date_to is not None:
        q += " AND date <= %s"
        params.append(date_to)
    q += " ORDER BY date"
    return pd.read_sql_query(q, conn, params=params)


def fetch_months_shrimp(conn: Any) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM months_shrimp ORDER BY date",
        conn,
    )
