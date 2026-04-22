#!/usr/bin/env python3
"""Export TP/FP/TN/FN confusion summaries for daily and monthly validation sets.

Usage:
  python -m services.supply_risk_training.export_confusion_metrics --model-dir models
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

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
    p = argparse.ArgumentParser(description="Export binary confusion matrices (TP/FP/TN/FN).")
    p.add_argument("--model-dir", type=Path, default=Path("models"))
    p.add_argument("--threshold", type=float, default=60.0, help="Positive class threshold on risk score.")
    p.add_argument(
        "--inclusive",
        action="store_true",
        help="Use >= threshold as positive (default uses > threshold).",
    )
    return p


def _positive_mask(s: pd.Series, threshold: float, inclusive: bool) -> pd.Series:
    if inclusive:
        return s >= threshold
    return s > threshold


def _confusion_counts(y_true: pd.Series, y_pred: pd.Series, threshold: float, inclusive: bool) -> dict[str, float]:
    yt = _positive_mask(y_true, threshold, inclusive)
    yp = _positive_mask(y_pred, threshold, inclusive)

    tp = int((yt & yp).sum())
    fp = int(((~yt) & yp).sum())
    tn = int(((~yt) & (~yp)).sum())
    fn = int((yt & (~yp)).sum())

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    accuracy = (tp + tn) / total if total else float("nan")
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else float("nan")

    return {
        "threshold": float(threshold),
        "inclusive": bool(inclusive),
        "n_rows": int(total),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "accuracy": float(accuracy),
    }


def main() -> None:
    args = _build_arg_parser().parse_args()

    manifest = json.loads((args.model_dir / "supply_risk_manifest.json").read_text())
    bundle = joblib.load(args.model_dir / "supply_risk_regression.joblib")

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
    y_pred_all = np.clip(y_month + delta, MANUAL_RISK_MIN, MANUAL_RISK_MAX)

    val = frame.loc[val_mask, ["date", "y"]].copy()
    val["y_pred"] = y_pred_all[val_mask.to_numpy()]
    val["label_ym"] = label_month_key_series(
        val["date"],
        label_month=manifest.get("label_month", "same"),
    )

    daily_counts = _confusion_counts(val["y"], val["y_pred"], args.threshold, args.inclusive)

    monthly = (
        val.groupby("label_ym", sort=False)
        .agg(y_true=("y", "mean"), y_pred=("y_pred", "mean"))
        .reset_index()
    )
    monthly_counts = _confusion_counts(monthly["y_true"], monthly["y_pred"], args.threshold, args.inclusive)

    out_daily_counts = args.model_dir / "confusion_daily_counts.csv"
    out_monthly_counts = args.model_dir / "confusion_monthly_counts.csv"
    out_daily_detail = args.model_dir / "validation_daily_predictions.csv"
    out_monthly_detail = args.model_dir / "validation_monthly_predictions.csv"

    pd.DataFrame([daily_counts]).to_csv(out_daily_counts, index=False)
    pd.DataFrame([monthly_counts]).to_csv(out_monthly_counts, index=False)

    val.rename(columns={"y": "y_true"}).to_csv(out_daily_detail, index=False)
    monthly.to_csv(out_monthly_detail, index=False)

    print(f"Wrote {out_daily_counts}")
    print(f"Wrote {out_monthly_counts}")
    print(f"Wrote {out_daily_detail}")
    print(f"Wrote {out_monthly_detail}")
    print("\nDaily confusion:")
    print(pd.DataFrame([daily_counts]).to_string(index=False))
    print("\nMonthly confusion:")
    print(pd.DataFrame([monthly_counts]).to_string(index=False))


if __name__ == "__main__":
    main()
