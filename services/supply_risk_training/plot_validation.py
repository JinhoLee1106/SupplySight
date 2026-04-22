#!/usr/bin/env python3
"""Generate presentation-ready validation charts for SupplySight models.

Usage:
  python -m services.supply_risk_training.plot_validation --model-dir models
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from services.supply_risk_training import supply_risk_db
from services.supply_risk_training.supply_risk_features import (
    build_training_frame,
    mask_valid_monthly_rows,
    train_validation_masks_by_month,
)
from services.supply_risk_training.supply_risk_labels import (
    MANUAL_RISK_MAX,
    MANUAL_RISK_MIN,
    daily_adjustment_oil_sentiment_batch,
    label_month_key_series,
    manual_baseline_adjustment_y,
)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate model validation plot for presentation.")
    p.add_argument("--model-dir", type=Path, default=Path("models"), help="Directory with manifest and trained bundles.")
    p.add_argument(
        "--output",
        type=Path,
        default=Path("models") / "validation_backtest_monthly.png",
        help="Output PNG path.",
    )
    return p


def main() -> None:
    args = _build_arg_parser().parse_args()
    model_dir = args.model_dir

    manifest_path = model_dir / "supply_risk_manifest.json"
    reg_path = model_dir / "supply_risk_regression.joblib"

    if not manifest_path.is_file() or not reg_path.is_file():
        raise FileNotFoundError(
            "Missing model artifacts. Run training first: "
            "python -m services.supply_risk_training --output-dir models --head both"
        )

    manifest = json.loads(manifest_path.read_text())
    bundle = joblib.load(reg_path)

    conn = supply_risk_db.connect()
    try:
        daily = supply_risk_db.fetch_dates_shrimp(conn, manifest.get("date_from"), manifest.get("date_to"))
        monthly = supply_risk_db.fetch_months_shrimp(conn)
    finally:
        conn.close()

    frame, _ = build_training_frame(
        daily,
        monthly,
        monthly_lag=manifest.get("monthly_lag", "same_month"),
    )
    frame = frame.loc[mask_valid_monthly_rows(frame)].reset_index(drop=True)

    holdout_months = int(manifest.get("holdout_months", 12))
    train_mask, val_mask = train_validation_masks_by_month(frame["date"], holdout_months)

    y, _ = manual_baseline_adjustment_y(
        frame,
        train_mask,
        label_month=manifest.get("label_month", "same"),
    )
    frame = frame.assign(y=y).loc[lambda d: d["y"].notna()].reset_index(drop=True)
    train_mask, val_mask = train_validation_masks_by_month(frame["date"], holdout_months)

    m_names = bundle["m_feature_names"]
    d_names = bundle["d_feature_names"]

    X = frame[m_names + d_names].astype(float).to_numpy()
    nm = len(m_names)

    Xm = pd.DataFrame(X[:, :nm], columns=m_names)
    Xm_i = bundle["imputer_month"].transform(Xm)
    y_month = np.asarray(bundle["rf_month"].predict(Xm_i), dtype=float)

    delta = daily_adjustment_oil_sentiment_batch(
        X[:, nm:],
        bundle["formula_meta"],
        bundle.get("d_oil_ix"),
        bundle.get("d_sent_ix"),
        delta_clip=float(bundle.get("delta_clip", 15.0)),
    )
    y_pred = np.clip(y_month + delta, MANUAL_RISK_MIN, MANUAL_RISK_MAX)

    val = frame.loc[val_mask, ["date", "y"]].copy()
    val["y_pred"] = y_pred[val_mask.to_numpy()]
    val["label_ym"] = label_month_key_series(
        val["date"],
        label_month=manifest.get("label_month", "same"),
    )

    monthly_plot = (
        val.groupby("label_ym", sort=False)
        .agg(y_true=("y", "mean"), y_pred=("y_pred", "mean"))
        .reset_index()
    )

    mae = mean_absolute_error(monthly_plot["y_true"], monthly_plot["y_pred"])

    plt.figure(figsize=(11, 5))
    plt.plot(monthly_plot["label_ym"], monthly_plot["y_true"], marker="o", label="Actual (monthly mean)")
    plt.plot(
        monthly_plot["label_ym"],
        monthly_plot["y_pred"],
        marker="o",
        linestyle="--",
        label="Predicted (monthly + daily adjustment)",
    )
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Risk score (1-100)")
    plt.xlabel("Validation month")
    plt.title(f"SupplySight Backtest Validation (holdout={holdout_months} months, MAE={mae:.2f})")
    plt.grid(alpha=0.2)
    plt.legend()
    plt.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output, dpi=180)

    print(f"Wrote {args.output}")
    print(monthly_plot.to_string(index=False))


if __name__ == "__main__":
    main()
