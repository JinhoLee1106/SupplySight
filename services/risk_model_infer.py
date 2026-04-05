#!/usr/bin/env python3
"""
services/risk_model_infer.py

Load trained supply risk model and predict from Postgres.

Example:
  python -m services.risk_model_infer --model-dir models
  python -m services.risk_model_infer --model-dir models --daily-date 2026-03-01
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from services import supply_risk_db
from services.supply_risk_features import build_training_frame


def predict_from_bundle(bundle: dict[str, Any], X_i: np.ndarray) -> float:
    if not bundle["two_stage"]:
        pred = bundle["model"].predict(X_i)[0]
        return float(np.clip(pred, 0.0, 100.0))

    m_idx, d_idx = bundle["m_idx"], bundle["d_idx"]
    Xm, Xd = X_i[:, m_idx], X_i[:, d_idx]
    bp = bundle["rf_baseline"].predict(Xm)
    Xdelta = np.column_stack([Xd, bp])
    out = bp[0] + bundle["rf_delta"].predict(Xdelta)[0]
    return float(np.clip(out, 0.0, 100.0))


def load_bundle(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "supply_risk_rf.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Missing model bundle: {path}")
    return joblib.load(path)


def load_manifest(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "supply_risk_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text())


def infer(
    *,
    model_dir: Path,
    daily_date: date | None = None,
) -> dict[str, Any]:
    bundle = load_bundle(model_dir)
    manifest = load_manifest(model_dir)

    monthly_lag = manifest.get("monthly_lag", "same_month")
    feature_names: list[str] = bundle["feature_names"]

    conn = supply_risk_db.connect()
    try:
        if daily_date is None:
            daily = supply_risk_db.fetch_dates_shrimp(conn)
            if daily.empty:
                raise RuntimeError("dates_shrimp is empty.")
            daily = daily.sort_values("date").iloc[[-1]]
        else:
            ds = daily_date.isoformat()
            daily = supply_risk_db.fetch_dates_shrimp(conn, date_from=ds, date_to=ds)
            if daily.empty:
                raise RuntimeError(f"No dates_shrimp row for date {ds}.")
        monthly = supply_risk_db.fetch_months_shrimp(conn)
    finally:
        conn.close()

    frame, _ = build_training_frame(daily, monthly, monthly_lag=monthly_lag)
    if len(frame) != 1:
        raise RuntimeError(f"Expected exactly one inference row, got {len(frame)}")
    row = frame.iloc[0]
    X = row[feature_names].astype(float).to_numpy().reshape(1, -1)
    X_i = bundle["imputer"].transform(X)
    score = predict_from_bundle(bundle, X_i)
    d = row["date"]
    if hasattr(d, "date"):
        d_out = d.isoformat() if hasattr(d, "isoformat") else str(d)
    else:
        d_out = str(d)

    return {
        "risk_score": round(score, 2),
        "model_dir": str(model_dir.resolve()),
        "daily_date": d_out,
        "monthly_lag": monthly_lag,
        "two_stage": bundle["two_stage"],
        "metrics_from_train": manifest.get("metrics"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Infer supply risk score from Postgres.")
    p.add_argument(
        "--model-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models",
    )
    p.add_argument("--daily-date", type=str, default=None, help="YYYY-MM-DD; default latest daily.")
    args = p.parse_args()
    d: date | None = None
    if args.daily_date:
        d = datetime.strptime(args.daily_date, "%Y-%m-%d").date()
    out = infer(model_dir=args.model_dir, daily_date=d)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
