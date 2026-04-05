#!/usr/bin/env python3
"""
Print date spans and calendar-month overlap for dates_shrimp vs months_shrimp.

Uses the same env as supply_risk_db (POSTGRES_*). Loads SupplySight/.env if present.

  python -m services.check_db_ranges
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
load_dotenv()

import pandas as pd

from services.supply_risk_training import supply_risk_db


def main() -> None:
    conn = supply_risk_db.connect()
    try:
        daily = pd.read_sql_query(
            "SELECT COUNT(*) AS n, MIN(date) AS dmin, MAX(date) AS dmax FROM dates_shrimp",
            conn,
        ).iloc[0]
        monthly = pd.read_sql_query(
            "SELECT COUNT(*) AS n, MIN(date) AS mmin, MAX(date) AS mmax FROM months_shrimp",
            conn,
        ).iloc[0]
        overlap = pd.read_sql_query(
            """
            WITH dm AS (
                SELECT DISTINCT date_trunc('month', date)::date AS m FROM dates_shrimp
            ),
            mm AS (
                SELECT DISTINCT date AS m FROM months_shrimp
            )
            SELECT COUNT(*) AS overlapping_calendar_months FROM dm INNER JOIN mm USING (m)
            """,
            conn,
        ).iloc[0]

        print("dates_shrimp (daily):")
        print(f"  rows={int(daily['n'])}, min_date={daily['dmin']}, max_date={daily['dmax']}")
        print("months_shrimp:")
        print(f"  rows={int(monthly['n'])}, min_date={monthly['mmin']}, max_date={monthly['mmax']}")
        print("overlap:")
        print(
            f"  distinct calendar months appearing in BOTH tables = {int(overlap['overlapping_calendar_months'])}"
        )
        if int(overlap["overlapping_calendar_months"]) == 0:
            print(
                "\n  No shared months: training labels will be all NaN. "
                "Align daily load and monthly ingest to the same calendar period."
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
