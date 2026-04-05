"""
Read-only FastAPI service for the React dashboard.

UNCERTAIN / PRODUCT NOTE (please confirm with domain owners):
- The UI speaks in 30/60/90 *day* risk horizons and multi-product portfolios.
- Postgres (`infra/init.sql`) only has `months_shrimp` and `dates_shrimp` — no per-SKU
  table and no stored forecast model outputs. We therefore:
  - expose a **single** logical product (shrimp / aggregate imports),
  - map horizons to **rolling windows of monthly history** (see `products` payload),
  - derive a 0–100 "risk score" from `monthly_import_zscore_6` heuristically.

News / articles are not in `init.sql`; evidence items are synthesized from
`dates_shrimp` when available. When the DB is down, `months_shrimp` is empty,
or a section has no real data yet, the API returns **labeled placeholders** so
the UI is testable (`meta.usingPlaceholders`, `meta.placeholderSections`).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Generator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = FastAPI(title="SupplySight Dashboard API", version="0.1.0")

_cors_origins = os.getenv(
    "SUPPLYSIGHT_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _pg_params() -> dict[str, Any]:
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", os.getenv("PGDATABASE", "postgres")),
        "user": os.getenv("POSTGRES_USER", os.getenv("PGUSER", "postgres")),
        "password": os.getenv("POSTGRES_PASSWORD", os.getenv("PGPASSWORD", "")),
    }


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    conn = psycopg2.connect(**_pg_params())
    try:
        yield conn
    finally:
        conn.close()


def _z_to_risk_score(z: float | None) -> tuple[int, str]:
    """
    UNCERTAIN: No formal risk model in repo. Map z-score to UI bucket + 0–100 score.
    """
    if z is None:
        return 50, "Medium"
    # Higher imports vs 6m norm might mean oversupply (lower risk) or noise — inverted here
    # so that *high positive z* reads as elevated disruption risk for demo purposes.
    score = int(max(0, min(100, round(50 + 12 * z))))
    if score < 35:
        return score, "Low"
    if score < 55:
        return score, "Medium"
    if score < 75:
        return score, "High"
    return score, "Critical"


def _trend_from_scores(current: int, older: int | None) -> str:
    if older is None:
        return "stable"
    if current > older + 3:
        return "up"
    if current < older - 3:
        return "down"
    return "stable"


def _fetch_months_shrimp(conn, limit: int = 48) -> list[dict[str, Any]]:
    q = """
        SELECT date, monthly_import, monthly_import_zscore_6, price_index_value,
               monthly_import_mom_pct, monthly_import_yoy_pct
        FROM months_shrimp
        ORDER BY date DESC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, (limit,))
        rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("date"), date):
            d["date"] = d["date"].isoformat()
        out.append(d)
    return list(reversed(out))


def _fetch_latest_dates_shrimp(conn) -> dict[str, Any] | None:
    q = """
        SELECT * FROM dates_shrimp
        ORDER BY date DESC
        LIMIT 1
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q)
        row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    if isinstance(d.get("date"), date):
        d["date"] = d["date"].isoformat()
    return d


# --- Placeholders for UI testing (uncertain / not-yet-modeled fields) -----------------

PLACEHOLDER_NOTE = "[Placeholder] Replace when forecasts, alerts, and evidence feeds exist."


def _placeholder_trend() -> list[dict[str, Any]]:
    """Synthetic monthly points so the chart renders without DB rows."""
    base = [
        (62, 1.02e7, 118.2),
        (64, 1.05e7, 119.0),
        (58, 9.8e6, 117.5),
        (55, 9.5e6, 116.8),
        (59, 9.9e6, 117.0),
        (61, 1.01e7, 117.8),
        (63, 1.03e7, 118.5),
        (67, 1.08e7, 119.2),
        (70, 1.10e7, 120.0),
        (72, 1.12e7, 120.4),
        (68, 1.09e7, 119.8),
        (71, 1.11e7, 120.1),
    ]
    return [
        {
            "date": f"2025-{i + 1:02d}",
            "shrimp": base[i][0],
            "monthlyImport": base[i][1],
            "priceIndex": base[i][2],
        }
        for i in range(len(base))
    ]


def _demo_non_shrimp_products() -> list[dict[str, Any]]:
    """Demo-only rows — no SupplySight pipeline for beef/beverages yet."""
    return [
        {
            "id": "PRD-002",
            "name": "Ribeye Steak",
            "category": "Beef",
            "supplier": "Premium Meat Co",
            "risk30": {"level": "Medium", "score": 15, "trend": "stable"},
            "risk60": {"level": "Medium", "score": 17, "trend": "up"},
            "risk90": {"level": "Medium", "score": 19, "trend": "up"},
        },
        {
            "id": "PRD-003",
            "name": "Asahi Beer",
            "category": "Beverages",
            "supplier": "Asahi Group Holdings",
            "risk30": {"level": "Low", "score": 11, "trend": "down"},
            "risk60": {"level": "Low", "score": 11, "trend": "down"},
            "risk90": {"level": "Low", "score": 10, "trend": "down"},
        },
    ]


def _placeholder_products() -> list[dict[str, Any]]:
    """Sample product rows — 30/60/90 are illustrative, not model output."""
    return [
        {
            "id": "PRD-PLACEHOLDER-001",
            "name": "Frozen Shrimp (placeholder)",
            "category": "Seafood",
            "supplier": "Pacific Harvest Ltd (placeholder)",
            "risk30": {"level": "High", "score": 72, "trend": "up"},
            "risk60": {"level": "Medium", "score": 58, "trend": "stable"},
            "risk90": {"level": "Low", "score": 42, "trend": "down"},
        },
        *_demo_non_shrimp_products(),
    ]


def _placeholder_overview() -> list[dict[str, Any]]:
    return [
        {
            "key": "risk",
            "label": "Overall Risk Level",
            "value": "Medium",
            "subtext": PLACEHOLDER_NOTE,
        },
        {
            "key": "products",
            "label": "Monitored Products",
            "value": "3",
            "subtext": PLACEHOLDER_NOTE,
        },
        {
            "key": "alerts",
            "label": "Active Alerts",
            "value": "4",
            "subtext": "2 critical, 2 warnings — " + PLACEHOLDER_NOTE,
        },
    ]


def _placeholder_evidence() -> list[dict[str, Any]]:
    return [
        {
            "iconType": "globe",
            "title": "Seafood supply disruption (placeholder)",
            "description": "Example copy for UI testing. Hook to news / dates_shrimp when ready.",
            "source": "Placeholder feed",
            "impact": "Critical",
            "date": "2026-03-15",
        },
        {
            "iconType": "trending",
            "title": "Feed cost volatility (placeholder)",
            "description": "Example macro signal. Replace with real commodity or model output.",
            "source": "Placeholder feed",
            "impact": "High",
            "date": "2026-03-16",
        },
    ]


def _placeholder_recommendations() -> list[dict[str, Any]]:
    return [
        {
            "iconType": "cart",
            "action": "Buy early (placeholder)",
            "product": "Frozen Shrimp",
            "description": "Sample mitigation action for layout testing.",
            "priority": "High",
            "savings": "Placeholder — model-driven estimate TBD",
            "timeline": "Action needed within 5 days (placeholder)",
        },
        {
            "iconType": "refresh",
            "action": "Diversify suppliers (placeholder)",
            "product": "Frozen Shrimp",
            "description": "Sample diversification suggestion for layout testing.",
            "priority": "High",
            "savings": "Placeholder — risk reduction TBD",
            "timeline": "Evaluate by end of quarter (placeholder)",
        },
    ]


def _full_placeholder_response(
    *,
    reason: str,
    db_error: str | None = None,
) -> dict[str, Any]:
    """All uncertain / empty sections filled so the UI is testable without real data."""
    meta: dict[str, Any] = {
        "asOf": "2026-03-01",
        "hasData": False,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "usingPlaceholders": True,
        "placeholderReason": reason,
        "placeholderSections": [
            "overview",
            "trend",
            "products",
            "evidence",
            "recommendations",
            "alerts",
        ],
    }
    if db_error:
        meta["dbError"] = db_error
    return {
        "meta": meta,
        "overview": _placeholder_overview(),
        "products": _placeholder_products(),
        "trend": _placeholder_trend(),
        "evidence": _placeholder_evidence(),
        "recommendations": _placeholder_recommendations(),
    }


def _overall_risk_label(months: list[dict[str, Any]]) -> tuple[str, str]:
    if not months:
        return "Unknown", "No monthly rows in months_shrimp"
    last = months[-1]
    _, level = _z_to_risk_score(
        float(last["monthly_import_zscore_6"])
        if last.get("monthly_import_zscore_6") is not None
        else None
    )
    mom = last.get("monthly_import_mom_pct")
    sub = "Latest month z-score bucket"
    if mom is not None:
        try:
            sub = f"MoM import change {float(mom):+.1f}% vs prior month"
        except (TypeError, ValueError):
            pass
    return level, sub


def build_dashboard_payload() -> dict[str, Any]:
    try:
        with get_conn() as conn:
            months = _fetch_months_shrimp(conn, limit=48)
            latest_day = _fetch_latest_dates_shrimp(conn)
    except psycopg2.OperationalError as e:
        return _full_placeholder_response(reason="database_unavailable", db_error=str(e))

    if not months:
        return _full_placeholder_response(reason="empty_months_shrimp")

    placeholder_sections: list[str] = []

    as_of = months[-1]["date"] if months else None
    overall_level, overall_sub = _overall_risk_label(months)

    # Trend points for chart (risk score per month from z-score)
    trend_points: list[dict[str, Any]] = []
    for m in months:
        z = m.get("monthly_import_zscore_6")
        zf = float(z) if z is not None else None
        score, _ = _z_to_risk_score(zf)
        label = m["date"][:7] if m.get("date") else ""
        trend_points.append(
            {
                "date": label,
                "shrimp": score,
                "monthlyImport": m.get("monthly_import"),
                "priceIndex": m.get("price_index_value"),
            }
        )

    # UNCERTAIN: 30/60/90 in UI are not true forecasts — see module docstring.
    products: list[dict[str, Any]] = []
    last3 = months[-3:]
    last6 = months[-6:]
    s30, l30 = _z_to_risk_score(
        float(last3[-1]["monthly_import_zscore_6"])
        if last3[-1].get("monthly_import_zscore_6") is not None
        else None
    )
    z60_vals = [
        float(x["monthly_import_zscore_6"])
        for x in last3
        if x.get("monthly_import_zscore_6") is not None
    ]
    z60_mean = sum(z60_vals) / len(z60_vals) if z60_vals else None
    s60, l60 = _z_to_risk_score(z60_mean)

    z90_vals = [
        float(x["monthly_import_zscore_6"])
        for x in last6
        if x.get("monthly_import_zscore_6") is not None
    ]
    z90_mean = sum(z90_vals) / len(z90_vals) if z90_vals else None
    s90, l90 = _z_to_risk_score(z90_mean)

    s30_prev, _ = _z_to_risk_score(
        float(last3[-2]["monthly_import_zscore_6"])
        if len(last3) >= 2 and last3[-2].get("monthly_import_zscore_6") is not None
        else None
    )
    products.append(
        {
            "id": "PRD-SHRIMP-001",
            "name": "Shrimp (aggregate imports)",
            "category": "Seafood",
            "supplier": "—",
            "risk30": {
                "level": l30,
                "score": s30,
                "trend": _trend_from_scores(s30, s30_prev if len(last3) >= 2 else None),
            },
            "risk60": {
                "level": l60,
                "score": s60,
                "trend": _trend_from_scores(s60, s30),
            },
            "risk90": {
                "level": l90,
                "score": s90,
                "trend": _trend_from_scores(s90, s60),
            },
        }
    )
    products.extend(_demo_non_shrimp_products())

    # Alerts: no pipeline in schema — always return placeholder counts for UI testing.
    alerts_placeholder = _placeholder_overview()[2]
    placeholder_sections.append("alerts")

    overview = [
        {
            "key": "risk",
            "label": "Overall Risk Level",
            "value": overall_level,
            "subtext": overall_sub,
        },
        {
            "key": "products",
            "label": "Monitored Products",
            "value": str(len(products)),
            "subtext": "Live row count from months_shrimp; portfolio size TBD — " + PLACEHOLDER_NOTE,
        },
        alerts_placeholder,
    ]

    evidence: list[dict[str, Any]] = []
    if latest_day and latest_day.get("sentiment_score") is not None:
        evidence.append(
            {
                "iconType": "trending",
                "title": "News sentiment feature",
                "description": f"Latest aggregated sentiment_score = {latest_day['sentiment_score']}",
                "source": "dates_shrimp.sentiment_score",
                "impact": "Medium",
                "date": latest_day.get("date") or "",
            }
        )
    if latest_day and latest_day.get("oil_price") is not None:
        evidence.append(
            {
                "iconType": "globe",
                "title": "Oil price (macro)",
                "description": f"Latest oil_price = {latest_day['oil_price']}",
                "source": "dates_shrimp.oil_price",
                "impact": "Low",
                "date": latest_day.get("date") or "",
            }
        )

    recommendations: list[dict[str, Any]] = []
    if months and months[-1].get("monthly_import_zscore_6") is not None:
        z = float(months[-1]["monthly_import_zscore_6"])
        if z >= 1.5:
            recommendations.append(
                {
                    "iconType": "cart",
                    "action": "Review supply plan",
                    "product": "Shrimp (aggregate imports)",
                    "description": "Import volume z-score vs 6-month history is elevated; validate with procurement.",
                    "priority": "High",
                    "savings": "Heuristic — replace with model output when available",
                    "timeline": f"As of {as_of or 'latest month'}",
                }
            )
        elif z <= -1.5:
            recommendations.append(
                {
                    "iconType": "refresh",
                    "action": "Monitor for oversupply",
                    "product": "Shrimp (aggregate imports)",
                    "description": "Import z-score is low vs recent history; confirm inventory coverage.",
                    "priority": "Medium",
                    "savings": "Heuristic — replace with model output when available",
                    "timeline": f"As of {as_of or 'latest month'}",
                }
            )

    if not evidence:
        evidence = _placeholder_evidence()
        placeholder_sections.append("evidence")
    if not recommendations:
        recommendations = _placeholder_recommendations()
        placeholder_sections.append("recommendations")

    return {
        "meta": {
            "asOf": as_of,
            "hasData": True,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "usingPlaceholders": bool(placeholder_sections),
            "placeholderSections": placeholder_sections,
        },
        "overview": overview,
        "products": products,
        "trend": trend_points,
        "evidence": evidence,
        "recommendations": recommendations,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def api_dashboard() -> dict[str, Any]:
    return build_dashboard_payload()


# Run: uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
# (from repo root, ensure PYTHONPATH includes repo root or use `python -m uvicorn ...`)
