#!/usr/bin/env python3
"""
services/supply_risk_training/supply_risk_train.py

Train from Postgres: labels ``y`` = ``manual_baseline_adjustment_y`` (``baseline_risk_tables`` +
formula adjustment). **One ``y`` for both heads.**

- Monthly linear score on ``m__`` (mean ``y`` per label month) + oil/sentiment **formula** delta on
  ``d__`` → bundle ``monthly_plus_formula_adjustment``.
- Optional monthly **classifier** (3-class) on the same ``m__`` block.

Examples::

  python -m services.supply_risk_training --output-dir models
  python -m services.supply_risk_training --head both --output-dir models
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
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import f1_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import supply_risk_db
from .supply_risk_features import (
    build_training_frame,
    mask_valid_monthly_rows,
    resolve_monthly_model_feature_names,
    train_validation_masks_by_month,
)
from .supply_risk_labels import (
    DELTA_CLIP_DEFAULT,
    LABEL_FORMULA_MANUAL,
    MANUAL_RISK_MAX,
    MANUAL_RISK_MIN,
    build_oil_sentiment_formula_meta,
    daily_adjustment_oil_sentiment_batch,
    label_month_key_series,
    manual_baseline_adjustment_y,
    risk_class_from_scores,
)

# Written artifacts (see ``train()``).
REGRESSION_JOB_NAME = "supply_risk_regression.joblib"
CLASSIFIER_JOB_NAME = "supply_risk_classifier.joblib"
LEGACY_COMBINED_JOB_NAME = "supply_risk_rf.joblib"


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train supply risk model from Postgres.")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "models",
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
    p.add_argument(
        "--holdout-months",
        type=int,
        default=12,
        help="Validation = last N calendar months (default 12).",
    )
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
    p.add_argument(
        "--delta-clip",
        type=float,
        default=DELTA_CLIP_DEFAULT,
        help="Clip formula daily adjustment to [-delta_clip, +delta_clip] before final score clip.",
    )
    p.add_argument(
        "--monthly-features",
        type=str,
        default=None,
        help=(
            "Comma-separated months_shrimp field names (no m__ prefix) for the monthly model; "
            "default uses MONTHLY_MODEL_FEATURES in supply_risk_features."
        ),
    )
    p.add_argument(
        "--head",
        choices=["regression", "classifier", "both"],
        default="both",
        help=(
            "Train only the monthly linear + formula score head (regression), only the "
            "3-class monthly classifier head, or both score+classifier. Separate .joblib files are "
            "written; manifest paths are merged so you can train heads independently."
        ),
    )
    return p


def _spearman(x: pd.Series, y: pd.Series) -> float:
    return float(x.corr(y, method="spearman"))


def _monthly_risk_class_truth(frame: pd.DataFrame, mask: pd.Series) -> pd.Series:
    """
    Per ``label_ym``, classification truth in ``0..2`` only: **mode** of daily
    ``risk_bucket(y)`` among rows where ``mask`` (not ``risk_bucket`` of the monthly mean score).

    ``y`` is the same column as for regression (``manual_baseline_adjustment_y``: baseline table
    + adjustment). Regression evaluates against mean ``y``; the classifier against these band ids.
    """
    sub = frame.loc[mask, ["label_ym", "y"]].copy()
    sub["c"] = risk_class_from_scores(sub["y"].to_numpy(dtype=float)).astype(np.int64)

    def _mode_int(s: pd.Series) -> int:
        m = s.mode()
        return int(m.iloc[0]) if len(m) > 0 else int(s.iloc[0])

    return sub.groupby("label_ym", sort=False)["c"].agg(_mode_int)


def _fit_monthly_linear(
    X_m_fit: np.ndarray,
    y_m_fit_arr: np.ndarray,
) -> tuple[Any, dict[str, Any]]:
    """Scaled OLS on month-level targets; ``predict`` compatible with inference."""
    est = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("lr", LinearRegression()),
        ]
    )
    est.fit(X_m_fit, y_m_fit_arr)
    meta = {"monthly_regressor": "linear_regression"}
    return est, meta


def _fit_monthly_classifier(
    X_m_fit: np.ndarray,
    y_class_fit: np.ndarray,
) -> tuple[Any | None, dict[str, Any]]:
    """
    Scaled random forest on month-level band labels 0..2 (low / average / high).
    Skipped if fewer than two distinct classes in the training months.
    """
    y_int = np.asarray(y_class_fit, dtype=int)
    if len(np.unique(y_int)) < 2:
        return None, {
            "monthly_classifier_kind": "skipped_few_classes",
            "n_classes": int(len(np.unique(y_int))),
        }
    est = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=12,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                    class_weight="balanced_subsample",
                ),
            ),
        ]
    )
    est.fit(X_m_fit, y_int)
    return est, {"monthly_classifier_kind": "random_forest"}


def _monthly_class_val_metrics(
    monthly_classifier: Any | None,
    month_rows: list[dict[str, Any]],
    val_f: pd.DataFrame,
    frame: pd.DataFrame,
    val_mask: pd.Series,
    imputer_month: SimpleImputer,
    m_names: list[str],
) -> dict[str, Any] | None:
    if monthly_classifier is None or not month_rows:
        return None
    val_month_class = _monthly_risk_class_truth(frame, val_mask)
    true_c: list[int] = []
    pred_c: list[int] = []
    for r in month_rows:
        ym = r["label_ym"]
        g = val_f.loc[val_f["label_ym"] == ym]
        if g.empty or ym not in val_month_class.index:
            continue
        true_c.append(int(val_month_class.loc[ym]))
        Xm0 = imputer_month.transform(g.iloc[[0]][m_names])
        pred_c.append(int(monthly_classifier.predict(Xm0)[0]))
    if not true_c:
        return None
    return {
        "accuracy_month_level": float(
            sum(int(a == b) for a, b in zip(true_c, pred_c)) / len(true_c)
        ),
        "f1_macro_month_level": float(
            f1_score(true_c, pred_c, average="macro", zero_division=0)
        ),
        "n_val_months_scored": len(true_c),
    }


def _bundle_monthly_classifier(
    monthly_classifier: Any,
    classifier_meta: dict[str, Any],
    m_names: list[str],
    imputer_month: SimpleImputer,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "bundle_role": "monthly_classifier",
        "architecture": "monthly_classifier_only",
        "model_version": "8",
        "m_feature_names": m_names,
        "imputer_month": imputer_month,
        "monthly_classifier": monthly_classifier,
        "monthly_classifier_kind": classifier_meta.get("monthly_classifier_kind"),
    }
    if classifier_meta.get("n_classes") is not None:
        out["monthly_classifier_n_classes_train"] = classifier_meta["n_classes"]
    return out


def _d_column_indices(d_names: list[str]) -> tuple[int | None, int | None]:
    oi = d_names.index("d__oil_price") if "d__oil_price" in d_names else None
    si = d_names.index("d__sentiment_score") if "d__sentiment_score" in d_names else None
    return oi, si


def _train_heads(
    args: argparse.Namespace,
    frame: pd.DataFrame,
    feature_names: list[str],
    m_names: list[str],
    train_mask: pd.Series,
    val_mask: pd.Series,
    manual_label_meta: dict[str, Any],
    *,
    head: str,
) -> dict[str, Any]:
    """
    Fit one or both heads. Returns a dict with ``regression_bundle``, ``classifier_bundle``,
    ``combined_bundle`` (for legacy single file when head is ``both``), ``manifest_extra``,
    and ``val_pred`` (None if regression not trained).
    """
    d_names = sorted(c for c in feature_names if c.startswith("d__"))
    if not m_names:
        raise RuntimeError("Training requires m__ columns.")
    if head in ("regression", "both") and not d_names:
        raise RuntimeError("Training requires d__ columns for formula adjustment.")

    frame = frame.copy()
    frame["label_ym"] = label_month_key_series(frame["date"], label_month=args.label_month)

    y_vec = frame["y"].astype(float)
    vm = val_mask.to_numpy(dtype=bool)

    train_f = frame.loc[train_mask]
    y_month_mean_train = train_f.groupby("label_ym", sort=False)["y"].mean()
    # Monthly training matrix: exactly one row per calendar label month (m__ is constant within month).
    monthly_train_m = train_f.groupby("label_ym", sort=False)[m_names].first()
    y_m_fit = y_month_mean_train.reindex(monthly_train_m.index)
    if y_m_fit.isna().any():
        ok = y_m_fit.notna()
        monthly_train_m = monthly_train_m.loc[ok]
        y_m_fit = y_m_fit.loc[ok]
    if len(monthly_train_m) < 2:
        raise RuntimeError(
            "Need at least 2 distinct label months in the training period for the monthly model."
        )

    train_month_class = _monthly_risk_class_truth(frame, train_mask)
    y_class_series = train_month_class.reindex(monthly_train_m.index)
    if y_class_series.isna().any():
        ok = y_class_series.notna()
        monthly_train_m = monthly_train_m.loc[ok]
        y_m_fit = y_m_fit.loc[ok]
        y_class_series = y_class_series.loc[ok]
    if len(monthly_train_m) < 2:
        raise RuntimeError(
            "Need at least 2 distinct label months after aligning class labels."
        )

    imputer_month = SimpleImputer(strategy="median")
    imputer_month.fit(monthly_train_m)
    X_m_fit = imputer_month.transform(monthly_train_m)
    y_m_fit_arr = y_m_fit.to_numpy(dtype=float)
    y_class_fit = y_class_series.astype(int).to_numpy()

    monthly_model = None
    monthly_meta: dict[str, Any] = {}
    y_month_pred: np.ndarray | None = None
    formula_meta: dict[str, Any] | None = None
    d_oil_ix: int | None = None
    d_sent_ix: int | None = None
    val_pred: np.ndarray | None = None
    mae = float("nan")
    spearman = float("nan")
    mae_month = float("nan")
    spearman_month = float("nan")

    if head in ("regression", "both"):
        monthly_model, monthly_meta = _fit_monthly_linear(X_m_fit, y_m_fit_arr)
        X_m_all = imputer_month.transform(frame[m_names])
        y_month_pred = monthly_model.predict(X_m_all)
        dc = float(args.delta_clip)
        X_all = frame[m_names + d_names].astype(float).to_numpy()
        nm = len(m_names)
        d_block_all = X_all[:, nm:]
        formula_meta = build_oil_sentiment_formula_meta(frame, train_mask)
        d_oil_ix, d_sent_ix = _d_column_indices(d_names)
        daily_res = daily_adjustment_oil_sentiment_batch(
            d_block_all, formula_meta, d_oil_ix, d_sent_ix, delta_clip=dc
        )
        val_pred = np.clip(
            y_month_pred[vm] + daily_res[vm], MANUAL_RISK_MIN, MANUAL_RISK_MAX
        )
        mae = mean_absolute_error(y_vec.loc[val_mask], val_pred)
        spearman = _spearman(
            y_vec.loc[val_mask].reset_index(drop=True), pd.Series(val_pred)
        )
        val_f = frame.loc[val_mask].copy()
        val_f["y_month_pred"] = y_month_pred[vm]
        month_rows_reg: list[dict[str, Any]] = []
        for ym, g in val_f.groupby("label_ym", sort=False):
            month_rows_reg.append(
                {
                    "label_ym": ym,
                    "y_mean": float(g["y"].mean()),
                    "y_month_pred": float(g["y_month_pred"].iloc[0]),
                }
            )
        if month_rows_reg:
            y_m_true = pd.Series([r["y_mean"] for r in month_rows_reg])
            y_m_p = pd.Series([r["y_month_pred"] for r in month_rows_reg])
            mae_month = mean_absolute_error(y_m_true, y_m_p)
            spearman_month = _spearman(y_m_true, y_m_p)

    monthly_classifier: Any | None = None
    classifier_meta: dict[str, Any] = {}
    if head in ("classifier", "both"):
        monthly_classifier, classifier_meta = _fit_monthly_classifier(X_m_fit, y_class_fit)

    val_f = frame.loc[val_mask].copy()
    if y_month_pred is not None:
        val_f["y_month_pred"] = y_month_pred[vm]
    month_rows: list[dict[str, Any]] = []
    for ym, g in val_f.groupby("label_ym", sort=False):
        row: dict[str, Any] = {
            "label_ym": ym,
            "y_mean": float(g["y"].mean()),
        }
        if "y_month_pred" in val_f.columns:
            row["y_month_pred"] = float(g["y_month_pred"].iloc[0])
        month_rows.append(row)

    metrics_class = _monthly_class_val_metrics(
        monthly_classifier,
        month_rows,
        val_f,
        frame,
        val_mask,
        imputer_month,
        m_names,
    )

    dc = float(args.delta_clip)
    regression_bundle: dict[str, Any] | None = None
    if head in ("regression", "both") and monthly_model is not None and formula_meta is not None:
        regression_bundle = {
            "architecture": "monthly_plus_formula_adjustment",
            "model_version": "8",
            "feature_names": m_names + d_names,
            "rf_month": monthly_model,
            "imputer_month": imputer_month,
            "m_feature_names": m_names,
            "d_feature_names": d_names,
            "formula_meta": formula_meta,
            "d_oil_ix": d_oil_ix,
            "d_sent_ix": d_sent_ix,
            "delta_clip": dc,
            "monthly_regressor": monthly_meta["monthly_regressor"],
        }

    classifier_bundle: dict[str, Any] | None = None
    if head in ("classifier", "both") and monthly_classifier is not None:
        classifier_bundle = _bundle_monthly_classifier(
            monthly_classifier, classifier_meta, m_names, imputer_month
        )

    combined_bundle: dict[str, Any] | None = None
    if head == "both" and regression_bundle is not None:
        combined_bundle = {**regression_bundle}
        if monthly_classifier is not None:
            combined_bundle["monthly_classifier"] = monthly_classifier
            combined_bundle["monthly_classifier_kind"] = classifier_meta.get(
                "monthly_classifier_kind"
            )
            if classifier_meta.get("n_classes") is not None:
                combined_bundle["monthly_classifier_n_classes_train"] = classifier_meta[
                    "n_classes"
                ]

    train_metrics: dict[str, Any] = {}
    if head in ("regression", "both") and val_pred is not None:
        train_metrics.update(
            {
                "mae": mae,
                "spearman": spearman,
                "mae_month_level": mae_month,
                "spearman_month_level": spearman_month,
            }
        )
    if metrics_class:
        train_metrics.update(metrics_class)

    manifest_extra: dict[str, Any] = {
        "metrics": train_metrics,
        "label_manual_meta": manual_label_meta,
        "delta_clip": dc,
        "n_train_months": int(len(y_m_fit_arr)),
        "train_head": head,
    }
    if head in ("regression", "both") and formula_meta is not None:
        manifest_extra["adjustment_formula"] = "oil_sentiment_train_minmax"
        manifest_extra["formula_meta"] = formula_meta
        manifest_extra["monthly_regressor"] = monthly_meta.get(
            "monthly_regressor", "linear_regression"
        )

    return {
        "regression_bundle": regression_bundle,
        "classifier_bundle": classifier_bundle,
        "combined_bundle": combined_bundle,
        "manifest_extra": manifest_extra,
        "val_pred": val_pred,
    }


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

    valid_m = mask_valid_monthly_rows(frame)
    n_before = len(frame)
    n_drop_monthly = int((~valid_m).sum())
    frame = frame.loc[valid_m].reset_index(drop=True)
    if frame.empty:
        raise RuntimeError(
            "No rows left after dropping days without required monthly features "
            f"(dropped {n_drop_monthly} / {n_before} rows with missing m__ zscore, price, or roll3_std)."
        )

    train_mask, val_mask = train_validation_masks_by_month(
        frame["date"], args.holdout_months
    )

    y_series, manual_label_meta = manual_baseline_adjustment_y(
        frame,
        train_mask,
        label_month=args.label_month,
    )
    if y_series.isna().all():
        raise RuntimeError(
            "No labeled rows: every day has NaN y (check BASELINE_RISK_BY_YM covers your months)."
        )

    frame = frame.copy()
    frame["y"] = y_series.to_numpy()

    frame = frame.loc[frame["y"].notna()].reset_index(drop=True)
    if frame.empty:
        raise RuntimeError(
            "No labeled rows after dropping NaN y (index alignment bug or all labels invalid)."
        )

    train_mask, val_mask = train_validation_masks_by_month(
        frame["date"], args.holdout_months
    )

    m_names = resolve_monthly_model_feature_names(
        feature_names, raw_override=args.monthly_features
    )

    fit_out = _train_heads(
        args,
        frame,
        feature_names,
        m_names,
        train_mask,
        val_mask,
        manual_label_meta,
        head=args.head,
    )
    regression_bundle = fit_out["regression_bundle"]
    classifier_bundle = fit_out["classifier_bundle"]
    if regression_bundle is None and classifier_bundle is None:
        raise RuntimeError(
            "No model artifact was saved (e.g. classifier skipped with a single training class). "
            "Use --head regression, widen the date range, or fix labels."
        )
    combined_bundle = fit_out["combined_bundle"]
    manifest_extra = fit_out["manifest_extra"]

    manifest_path = out_dir / "supply_risk_manifest.json"
    prev: dict[str, Any] = {}
    if manifest_path.exists():
        prev = json.loads(manifest_path.read_text())

    paths_note: list[str] = []
    regression_path: Path | None = None
    classifier_path: Path | None = None
    legacy_path: Path | None = None

    if regression_bundle is not None:
        regression_path = out_dir / REGRESSION_JOB_NAME
        joblib.dump(regression_bundle, regression_path)
        paths_note.append(str(regression_path.resolve()))

    if classifier_bundle is not None:
        classifier_path = out_dir / CLASSIFIER_JOB_NAME
        joblib.dump(classifier_bundle, classifier_path)
        paths_note.append(str(classifier_path.resolve()))

    if args.head == "both" and combined_bundle is not None:
        legacy_path = out_dir / LEGACY_COMBINED_JOB_NAME
        joblib.dump(combined_bundle, legacy_path)
        paths_note.append(str(legacy_path.resolve()))

    d_list = sorted(c for c in feature_names if c.startswith("d__"))
    if regression_bundle is not None:
        feat_names = regression_bundle["feature_names"]
        m_feat = regression_bundle["m_feature_names"]
        d_feat = regression_bundle["d_feature_names"]
    elif classifier_bundle is not None:
        m_feat = classifier_bundle["m_feature_names"]
        d_feat = d_list
        feat_names = m_feat + d_feat
    else:
        raise RuntimeError("Training produced no artifact (check --head and data).")

    clf_kind = None
    if classifier_bundle is not None:
        clf_kind = classifier_bundle.get("monthly_classifier_kind")
    elif prev.get("monthly_classifier_kind"):
        clf_kind = prev.get("monthly_classifier_kind")
    elif combined_bundle is not None:
        clf_kind = combined_bundle.get("monthly_classifier_kind")

    reg_arch: str | None = None
    if regression_bundle is not None:
        reg_arch = str(regression_bundle.get("architecture", "")) or None
    elif combined_bundle is not None:
        reg_arch = str(combined_bundle.get("architecture", "")) or None

    manifest: dict[str, Any] = {
        "version": "2",
        "model_version": "8",
        "architecture": reg_arch
        or prev.get("architecture")
        or "monthly_plus_formula_adjustment",
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "label_mode": "manual_baseline_adjustment",
        "label_formula": LABEL_FORMULA_MANUAL,
        "label_score_min": MANUAL_RISK_MIN,
        "label_score_max": MANUAL_RISK_MAX,
        "monthly_lag": args.monthly_lag,
        "label_month": args.label_month,
        "holdout_months": args.holdout_months,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "n_rows_dropped_missing_monthly": n_drop_monthly,
        "n_rows_total": len(frame),
        "n_train": int(train_mask.sum()),
        "n_val": int(val_mask.sum()),
        "train_date_min": str(frame.loc[train_mask, "date"].min().date()),
        "train_date_max": str(frame.loc[train_mask, "date"].max().date()),
        "monthly_head": "linear_regression_scaled",
        "train_head": args.head,
        "monthly_classifier_kind": clf_kind,
        "regression_model_path": str(regression_path.resolve()) if regression_path else prev.get("regression_model_path"),
        "classifier_model_path": str(classifier_path.resolve()) if classifier_path else prev.get("classifier_model_path"),
        "model_path": str(legacy_path.resolve()) if legacy_path else prev.get("model_path"),
        "feature_names": feat_names,
        "m_feature_names": m_feat,
        "d_feature_names": d_feat,
        "monthly_features_cli": args.monthly_features,
        **manifest_extra,
    }
    # Preserve sibling artifact paths from a previous run if this run did not rewrite them.
    if regression_path is None and prev.get("regression_model_path"):
        manifest["regression_model_path"] = prev["regression_model_path"]
    if classifier_path is None and prev.get("classifier_model_path"):
        manifest["classifier_model_path"] = prev["classifier_model_path"]
    if legacy_path is None and prev.get("model_path"):
        manifest["model_path"] = prev["model_path"]

    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(json.dumps(manifest.get("metrics", {}), indent=2))
    for p in paths_note:
        print(f"Wrote {p}")
    print(f"Wrote {manifest_path}")
    return manifest


def main() -> None:
    args = _build_arg_parser().parse_args()
    train(args)


if __name__ == "__main__":
    main()
