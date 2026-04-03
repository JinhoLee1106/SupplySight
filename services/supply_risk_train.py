#!/usr/bin/env python3
"""
services/supply_risk_train.py

Train Random Forest supply risk model from Postgres (months_shrimp + dates_shrimp).

Example:
  python -m services.supply_risk_train --output-dir models
  python -m services.supply_risk_train --monthly-lag prev_month --label-month next --two-stage
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error

from services import supply_risk_db
from services.supply_risk_features import (
    build_training_frame,
    train_validation_masks_by_month,
)
from services.supply_risk_labels import (
    LABEL_FORMULA_V1,
    attach_labels_to_days,
    monthly_scaled_labels,
)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train supply risk Random Forest from Postgres.")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models",
        help="Directory for supply_risk_rf.joblib and supply_risk_manifest.json",
    )
    p.add_argument(
        "--monthly-lag",
        choices=["same_month", "prev_month"],
        default="same_month",
        help="Join key: same calendar month or previous month (vs months_shrimp.date).",
    )
    p.add_argument(
        "--label-month",
        choices=["same", "next"],
        default="same",
        help="Label: y(M) for days in month M, or y(M+1).",
    )
    p.add_argument("--holdout-months", type=int, default=6, help="Validation = last N months.")
    p.add_argument(
        "--date-from",
        type=str,
        default=None,
        help="Optional YYYY-MM-DD lower bound on dates_shrimp.",
    )
    p.add_argument(
        "--date-to",
        type=str,
        default=None,
        help="Optional YYYY-MM-DD upper bound on dates_shrimp.",
    )
    p.add_argument("--p-ref", type=float, default=90.0, help="Price reference in label proxy.")
    p.add_argument(
        "--two-stage",
        action="store_true",
        help="Train baseline RF on m__* then delta RF on d__* + baseline_pred.",
    )
    p.add_argument("--n-estimators", type=int, default=300)
    p.add_argument("--random-state", type=int, default=42)
    return p


def _spearman(x: pd.Series, y: pd.Series) -> float:
    return float(x.corr(y, method="spearman"))


def train(args: argparse.Namespace) -> dict[str, Any]:
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = supply_risk_db.connect()
    try:
        daily = supply_risk_db.fetch_dates_shrimp(conn, args.date_from, args.date_to)
        monthly = supply_risk_db.fetch_months_shrimp(conn)
    finally:
        conn.close()

    if daily.empty or monthly.empty:
        raise RuntimeError("Need non-empty dates_shrimp and months_shrimp from database.")

    frame, feature_names = build_training_frame(
        daily, monthly, monthly_lag=args.monthly_lag
    )

    train_mask, val_mask = train_validation_masks_by_month(
        frame["date"], args.holdout_months
    )

    y_month = monthly_scaled_labels(monthly, frame.loc[train_mask, "date"], p_ref=args.p_ref)
    y = attach_labels_to_days(frame["date"], y_month, label_month=args.label_month)
    frame = frame.assign(y=y)
    frame = frame.loc[frame["y"].notna()].reset_index(drop=True)

    train_mask, val_mask = train_validation_masks_by_month(
        frame["date"], args.holdout_months
    )

    X = frame[feature_names].astype(float)
    y_vec = frame["y"].astype(float)

    X_train, X_val = X.loc[train_mask], X.loc[val_mask]
    y_train, y_val = y_vec.loc[train_mask], y_vec.loc[val_mask]

    imputer = SimpleImputer(strategy="median")
    X_train_i = imputer.fit_transform(X_train)
    X_val_i = imputer.transform(X_val)

    m_idx = [i for i, c in enumerate(feature_names) if c.startswith("m__")]
    d_idx = [i for i, c in enumerate(feature_names) if c.startswith("d__")]

    rf_params = {
        "n_estimators": args.n_estimators,
        "random_state": args.random_state,
        "min_samples_leaf": 2,
        "n_jobs": -1,
    }

    if not args.two_stage:
        rf = RandomForestRegressor(**rf_params)
        rf.fit(X_train_i, y_train)
        val_pred = rf.predict(X_val_i)
        bundle: dict[str, Any] = {
            "two_stage": False,
            "imputer": imputer,
            "feature_names": feature_names,
            "m_idx": m_idx,
            "d_idx": d_idx,
            "model": rf,
            "rf_baseline": None,
            "rf_delta": None,
        }
    else:
        Xm_tr, Xd_tr = X_train_i[:, m_idx], X_train_i[:, d_idx]
        Xm_va, Xd_va = X_val_i[:, m_idx], X_val_i[:, d_idx]

        rf_b = RandomForestRegressor(**rf_params)
        rf_b.fit(Xm_tr, y_train)
        bp_tr = rf_b.predict(Xm_tr)
        residual = y_train.to_numpy() - bp_tr
        Xdelta_tr = np.column_stack([Xd_tr, bp_tr])

        rf_d = RandomForestRegressor(**rf_params)
        rf_d.fit(Xdelta_tr, residual)

        bp_va = rf_b.predict(Xm_va)
        Xdelta_va = np.column_stack([Xd_va, bp_va])
        val_pred = np.clip(bp_va + rf_d.predict(Xdelta_va), 0.0, 100.0)

        bundle = {
            "two_stage": True,
            "imputer": imputer,
            "feature_names": feature_names,
            "m_idx": m_idx,
            "d_idx": d_idx,
            "model": None,
            "rf_baseline": rf_b,
            "rf_delta": rf_d,
        }

    mae = mean_absolute_error(y_val, val_pred)
    spearman = _spearman(y_val.reset_index(drop=True), pd.Series(val_pred))

    model_path = out_dir / "supply_risk_rf.joblib"
    joblib.dump(bundle, model_path)

    manifest = {
        "version": "1",
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "label_formula": LABEL_FORMULA_V1,
        "p_ref": args.p_ref,
        "monthly_lag": args.monthly_lag,
        "label_month": args.label_month,
        "two_stage": args.two_stage,
        "feature_names": feature_names,
        "holdout_months": args.holdout_months,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "n_rows_total": len(frame),
        "n_train": int(train_mask.sum()),
        "n_val": int(val_mask.sum()),
        "train_date_min": str(frame.loc[train_mask, "date"].min().date()),
        "train_date_max": str(frame.loc[train_mask, "date"].max().date()),
        "metrics": {"mae": mae, "spearman": spearman},
        "rf_params": rf_params,
        "model_path": str(model_path.resolve()),
    }

    manifest_path = out_dir / "supply_risk_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(json.dumps(manifest["metrics"], indent=2))
    print(f"Wrote {model_path}")
    print(f"Wrote {manifest_path}")
    return manifest


def main() -> None:
    args = _build_arg_parser().parse_args()
    train(args)


if __name__ == "__main__":
    main()
