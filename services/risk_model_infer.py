#!/usr/bin/env python3
"""
services/risk_model_infer.py

Load trained supply risk models from ``models/``: regression (1–100 score) and optional
separate classifier bundle for **3** risk bands (low / average / high). Uses ``supply_risk_manifest.json`` paths;
falls back to ``supply_risk_regression.joblib`` / ``supply_risk_rf.joblib``.

Example:
  python -m services.risk_model_infer --model-dir models
  python -m services.risk_model_infer --model-dir models --daily-date 2026-03-01
  python -m services.risk_model_infer --model-dir models --last-years 2
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
from dateutil.relativedelta import relativedelta

from services.supply_risk_training import supply_risk_db
from services.supply_risk_training.supply_risk_features import (
    build_training_frame,
    describe_monthly_validation_failure,
    mask_valid_monthly_rows,
    month_anchor,
)
from services.supply_risk_training.supply_risk_labels import (
    DELTA_CLIP_DEFAULT,
    LABEL_SCORE_MAX,
    LABEL_SCORE_MIN,
    RISK_CLASS_LABELS,
    daily_adjustment_oil_sentiment_batch,
    risk_bucket,
    risk_class_from_scores,
    risk_class_label,
)


def raw_predict_from_bundle(bundle: dict[str, Any], X_i: np.ndarray) -> float:
    out = raw_predict_batch(bundle, X_i)
    return float(out[0])


def predict_risk_class_batch_from_bundle(
    bundle: dict[str, Any], X_i: np.ndarray
) -> np.ndarray | None:
    """
    Month-level classifier (e.g. random forest): same ``m__`` block as ``rf_month``, one band id
    (0..2: low / average / high) per row.
    Pass the **classifier** sidecar bundle or a **combined** regression bundle that embeds
    ``monthly_classifier``. Returns ``None`` if there is no classifier (fall back to score buckets).
    """
    clf = bundle.get("monthly_classifier")
    if clf is None:
        return None
    m_names = bundle["m_feature_names"]
    nm = len(m_names)
    Xm = bundle["imputer_month"].transform(X_i[:, :nm])
    return np.asarray(clf.predict(Xm), dtype=np.int64)


def load_regression_bundle(model_dir: Path, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Score path: scaled linear monthly head + formula adjustment. Resolution order: manifest
    ``regression_model_path``, ``model_path`` (legacy), ``supply_risk_regression.joblib``,
    ``supply_risk_rf.joblib``.
    """
    manifest = manifest or load_manifest(model_dir)
    candidates: list[Path] = []
    for key in ("regression_model_path", "model_path"):
        raw = manifest.get(key)
        if raw:
            candidates.append(Path(raw))
    candidates.extend(
        [model_dir / REGRESSION_JOB_NAME, model_dir / LEGACY_COMBINED_JOB_NAME]
    )
    seen: set[Path] = set()
    for p in candidates:
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if p.is_file():
            return joblib.load(p)
    raise FileNotFoundError(
        f"No regression bundle in {model_dir}. Train with: "
        "python -m services.supply_risk_training --head regression --output-dir ... "
        f"or ensure {REGRESSION_JOB_NAME} / {LEGACY_COMBINED_JOB_NAME} exists."
    )


def load_classifier_bundle_optional(
    model_dir: Path,
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    """Optional sidecar from ``--head classifier`` / ``both`` (random forest monthly classifier)."""
    raw = manifest.get("classifier_model_path")
    if raw:
        p = Path(raw)
        if p.is_file():
            return joblib.load(p)
    p2 = model_dir / CLASSIFIER_JOB_NAME
    if p2.is_file():
        return joblib.load(p2)
    return None


def _risk_class_source_from_bundle(class_bundle: dict[str, Any]) -> str:
    k = class_bundle.get("monthly_classifier_kind")
    if k in ("random_forest", None):
        return "monthly_rf"
    return "monthly_classifier"


def bundle_for_class_prediction(
    regression_bundle: dict[str, Any],
    classifier_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prefer sidecar classifier; else embedded ``monthly_classifier`` on the regression bundle."""
    if classifier_bundle is not None:
        return classifier_bundle
    return regression_bundle


def raw_predict_batch(bundle: dict[str, Any], X_i: np.ndarray) -> np.ndarray:
    """One raw score per row of ``X_i`` (columns = ``bundle['feature_names']`` order)."""
    arch = bundle.get("architecture")
    m_names = bundle["m_feature_names"]
    nm = len(m_names)
    nd = len(bundle["d_feature_names"])
    if X_i.shape[1] != nm + nd:
        raise ValueError(
            f"Expected {nm + nd} features (m__ + d__), got {X_i.shape[1]}"
        )
    Xm = bundle["imputer_month"].transform(X_i[:, :nm])
    monthly_risk = np.asarray(bundle["rf_month"].predict(Xm), dtype=float)
    dc = float(bundle.get("delta_clip", DELTA_CLIP_DEFAULT))

    if arch == "monthly_plus_formula_adjustment":
        d_block = X_i[:, nm : nm + nd]
        delta = daily_adjustment_oil_sentiment_batch(
            d_block,
            bundle["formula_meta"],
            bundle.get("d_oil_ix"),
            bundle.get("d_sent_ix"),
            delta_clip=dc,
        )
        return np.asarray(monthly_risk + delta, dtype=float)

    if arch == "monthly_plus_daily_delta":
        Xd = bundle["imputer_delta"].transform(X_i[:, nm : nm + nd])
        delta_raw = bundle["rf_delta"].predict(np.column_stack([Xd, monthly_risk]))
        return np.asarray(monthly_risk + np.clip(delta_raw, -dc, dc), dtype=float)

    raise ValueError(
        f"Unsupported bundle architecture {arch!r}; "
        "retrain with services.supply_risk_training or use a compatible bundle."
    )


def decomposed_components_from_bundle(
    bundle: dict[str, Any], X_i: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    ``(monthly_risk, daily_adjustment_clipped, raw_sum)`` per row.
    """
    arch = bundle.get("architecture")
    m_names = bundle["m_feature_names"]
    nm = len(m_names)
    nd = len(bundle["d_feature_names"])
    Xm = bundle["imputer_month"].transform(X_i[:, :nm])
    monthly_risk = np.asarray(bundle["rf_month"].predict(Xm), dtype=float)
    dc = float(bundle.get("delta_clip", DELTA_CLIP_DEFAULT))

    if arch == "monthly_plus_formula_adjustment":
        d_block = X_i[:, nm : nm + nd]
        delta = daily_adjustment_oil_sentiment_batch(
            d_block,
            bundle["formula_meta"],
            bundle.get("d_oil_ix"),
            bundle.get("d_sent_ix"),
            delta_clip=dc,
        )
        return monthly_risk, delta, monthly_risk + delta

    if arch == "monthly_plus_daily_delta":
        Xd = bundle["imputer_delta"].transform(X_i[:, nm : nm + nd])
        delta_raw = np.asarray(
            bundle["rf_delta"].predict(np.column_stack([Xd, monthly_risk])), dtype=float
        )
        delta = np.clip(delta_raw, -dc, dc)
        return monthly_risk, delta, monthly_risk + delta

    raise ValueError(
        f"Unsupported bundle architecture {arch!r}; "
        "retrain with services.supply_risk_training or use a compatible bundle."
    )


def predict_from_bundle(
    bundle: dict[str, Any],
    X_i: np.ndarray,
    *,
    score_min: float = LABEL_SCORE_MIN,
    score_max: float = LABEL_SCORE_MAX,
) -> float:
    """Clip final score; ``X_i`` is raw ``m__`` then ``d__`` in ``feature_names`` order."""
    _, _, raw_sum = decomposed_components_from_bundle(bundle, X_i)
    return float(np.clip(raw_sum[0], score_min, score_max))


_ARCHITECTURES_OK = frozenset(
    {"monthly_plus_formula_adjustment", "monthly_plus_daily_delta"}
)

# Artifact names (keep in sync with services.supply_risk_training.supply_risk_train).
REGRESSION_JOB_NAME = "supply_risk_regression.joblib"
CLASSIFIER_JOB_NAME = "supply_risk_classifier.joblib"
LEGACY_COMBINED_JOB_NAME = "supply_risk_rf.joblib"


def _nan_counts_for_features(row: pd.Series, feature_names: list[str]) -> dict[str, int]:
    s = row[feature_names]
    m_names = [c for c in feature_names if c.startswith("m__")]
    d_names = [c for c in feature_names if c.startswith("d__")]
    return {
        "n_features_nan": int(s.isna().sum()),
        "n_m_features_nan": int(s[m_names].isna().sum()) if m_names else 0,
        "n_d_features_nan": int(s[d_names].isna().sum()) if d_names else 0,
    }


def load_bundle(model_dir: Path) -> dict[str, Any]:
    """Backward-compatible alias: load the regression (score) bundle."""
    return load_regression_bundle(model_dir)


def load_manifest(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "supply_risk_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text())


def infer(
    *,
    model_dir: Path,
    daily_date: date | None = None,
    debug: bool = False,
) -> dict[str, Any]:
    manifest = load_manifest(model_dir)
    bundle = load_regression_bundle(model_dir, manifest)
    classifier_bundle = load_classifier_bundle_optional(model_dir, manifest)
    class_bundle = bundle_for_class_prediction(bundle, classifier_bundle)

    if bundle.get("architecture") not in _ARCHITECTURES_OK:
        raise RuntimeError(
            f"Model at {model_dir} has architecture {bundle.get('architecture')!r}. "
            "Retrain with: python -m services.supply_risk_training --output-dir <dir>"
        )

    score_min = float(manifest.get("label_score_min", LABEL_SCORE_MIN))
    score_max = float(manifest.get("label_score_max", LABEL_SCORE_MAX))

    monthly_lag = manifest.get("monthly_lag", "same_month")
    feature_names: list[str] = bundle["feature_names"]

    conn = supply_risk_db.connect()
    try:
        if daily_date is None:
            daily_all = supply_risk_db.fetch_dates_shrimp(conn)
            if daily_all.empty:
                raise RuntimeError("dates_shrimp is empty.")
            daily_all = daily_all.sort_values("date")
        else:
            ds = daily_date.isoformat()
            daily_all = supply_risk_db.fetch_dates_shrimp(conn, date_from=ds, date_to=ds)
            if daily_all.empty:
                raise RuntimeError(f"No dates_shrimp row for date {ds}.")
        monthly = supply_risk_db.fetch_months_shrimp(conn)
    finally:
        conn.close()

    frame, _ = build_training_frame(daily_all, monthly, monthly_lag=monthly_lag)
    used_latest_valid_daily = False
    if daily_date is None:
        valid_m = mask_valid_monthly_rows(frame)
        if not bool(valid_m.any()):
            last = frame.iloc[-1]
            raise RuntimeError(
                "No day in dates_shrimp has valid monthly features. "
                f"Last day tried: {describe_monthly_validation_failure(last, monthly_lag)}. "
                "Load or fix months_shrimp for that month (finite zscore, price_index, roll3_std)."
            )
        last_ok = frame.loc[valid_m].index[-1]
        frame = frame.loc[[last_ok]].reset_index(drop=True)
        latest_dt = pd.to_datetime(daily_all["date"]).max()
        scored_dt = pd.to_datetime(frame["date"].iloc[0])
        used_latest_valid_daily = bool(scored_dt.normalize() < latest_dt.normalize())
    else:
        if len(frame) != 1:
            raise RuntimeError(f"Expected exactly one inference row, got {len(frame)}")
        if not bool(mask_valid_monthly_rows(frame).iloc[0]):
            r0 = frame.iloc[0]
            raise RuntimeError(
                "Missing monthly features for this day. "
                f"{describe_monthly_validation_failure(r0, monthly_lag)}. "
                "Ensure months_shrimp has a row for the join month with finite required fields."
            )
    row = frame.iloc[0]
    X = row[feature_names].astype(float).to_numpy().reshape(1, -1)
    monthly_risk_arr, daily_adj_arr, raw_sum = decomposed_components_from_bundle(
        bundle, X
    )
    raw_score = float(raw_sum[0])
    monthly_risk_v = float(monthly_risk_arr[0])
    daily_adj_v = float(daily_adj_arr[0])
    score = float(np.clip(raw_score, score_min, score_max))
    risk_score_rounded = round(score, 2)
    risk_class_from_score = risk_bucket(risk_score_rounded)
    cls_batch = predict_risk_class_batch_from_bundle(class_bundle, X)
    if cls_batch is not None:
        risk_class = int(cls_batch[0])
        risk_class_source = _risk_class_source_from_bundle(class_bundle)
    else:
        risk_class = risk_class_from_score
        risk_class_source = "score_bucket"
    d = row["date"]
    if hasattr(d, "date"):
        d_out = d.isoformat() if hasattr(d, "isoformat") else str(d)
    else:
        d_out = str(d)

    out: dict[str, Any] = {
        "risk_score": risk_score_rounded,
        "risk_class": risk_class,
        "risk_class_label": risk_class_label(risk_class),
        "risk_class_source": risk_class_source,
        "risk_class_from_score": risk_class_from_score,
        "risk_class_label_from_score": risk_class_label(risk_class_from_score),
        "monthly_classifier_kind": class_bundle.get("monthly_classifier_kind"),
        "classifier_bundle_sidecar": classifier_bundle is not None,
        "model_dir": str(model_dir.resolve()),
        "daily_date": d_out,
        "monthly_lag": monthly_lag,
        "architecture": bundle["architecture"],
        "monthly_regressor": bundle.get("monthly_regressor", "linear_regression"),
        "metrics_from_train": manifest.get("metrics"),
        "monthly_risk": round(monthly_risk_v, 2),
        "daily_adjustment": round(daily_adj_v, 2),
    }
    if used_latest_valid_daily:
        out["note"] = (
            "Scored the latest day that has complete monthly features; more recent dates_shrimp "
            "rows are missing months_shrimp for their month or have null required m__ fields. "
            "Refresh monthly pipelines or pass --daily-date for a specific day."
        )
    if debug:
        m_anchor = month_anchor(pd.Series([row["date"]]), monthly_lag).iloc[0]
        if hasattr(m_anchor, "isoformat"):
            mk = m_anchor.isoformat()
        else:
            mk = str(m_anchor)
        out["debug"] = {
            "risk_score_raw": raw_score,
            "score_clip": [score_min, score_max],
            "monthly_join_key": mk,
            **_nan_counts_for_features(row, feature_names),
        }
    return out


def infer_date_range(
    *,
    model_dir: Path,
    date_from: date,
    date_to: date,
) -> pd.DataFrame:
    """
    One risk score per day between ``date_from`` and ``date_to`` (inclusive) that has valid
    monthly features; days without a ``months_shrimp`` join or with null required ``m__`` fields are omitted.
    """
    manifest = load_manifest(model_dir)
    bundle = load_regression_bundle(model_dir, manifest)
    classifier_bundle = load_classifier_bundle_optional(model_dir, manifest)
    class_bundle = bundle_for_class_prediction(bundle, classifier_bundle)
    if bundle.get("architecture") not in _ARCHITECTURES_OK:
        raise RuntimeError(
            f"Model has architecture {bundle.get('architecture')!r}; retrain with services.supply_risk_training."
        )
    score_min = float(manifest.get("label_score_min", LABEL_SCORE_MIN))
    score_max = float(manifest.get("label_score_max", LABEL_SCORE_MAX))
    monthly_lag = manifest.get("monthly_lag", "same_month")
    feature_names: list[str] = bundle["feature_names"]

    conn = supply_risk_db.connect()
    try:
        daily = supply_risk_db.fetch_dates_shrimp(
            conn,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        )
        monthly = supply_risk_db.fetch_months_shrimp(conn)
    finally:
        conn.close()

    if daily.empty:
        raise RuntimeError(
            f"No dates_shrimp rows between {date_from.isoformat()} and {date_to.isoformat()}."
        )

    frame, _ = build_training_frame(daily, monthly, monthly_lag=monthly_lag)
    valid_m = mask_valid_monthly_rows(frame)
    n_skip = int((~valid_m).sum())
    frame = frame.loc[valid_m].reset_index(drop=True)
    if frame.empty:
        raise RuntimeError(
            f"No rows with valid monthly data in range ({n_skip} day(s) dropped: missing months_shrimp join or null m__ fields)."
        )
    X = frame[feature_names].astype(float).to_numpy()
    monthly_risk, daily_adj, raw_sum = decomposed_components_from_bundle(bundle, X)
    scores = np.clip(raw_sum, score_min, score_max)
    rs = np.round(scores, 2)
    rc_from_score = risk_class_from_scores(rs)
    cls_trained = predict_risk_class_batch_from_bundle(class_bundle, X)
    if cls_trained is not None:
        rc = cls_trained
        src = _risk_class_source_from_bundle(class_bundle)
        rc_src = np.full(len(frame), src, dtype=object)
    else:
        rc = rc_from_score
        rc_src = np.full(len(frame), "score_bucket", dtype=object)
    dates = pd.to_datetime(frame["date"])
    return pd.DataFrame(
        {
            "date": dates.dt.strftime("%Y-%m-%d"),
            "risk_score": rs,
            "risk_class": rc,
            "risk_class_label": [RISK_CLASS_LABELS[int(c)] for c in rc],
            "risk_class_source": rc_src,
            "risk_class_from_score": rc_from_score,
            "risk_class_label_from_score": [
                RISK_CLASS_LABELS[int(c)] for c in rc_from_score
            ],
            "monthly_risk": np.round(monthly_risk, 2),
            "daily_adjustment": np.round(daily_adj, 2),
        }
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Infer supply risk score from Postgres.")
    p.add_argument(
        "--model-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models",
    )
    p.add_argument("--daily-date", type=str, default=None, help="YYYY-MM-DD; default latest daily.")
    p.add_argument(
        "--date-from",
        type=str,
        default=None,
        help="With --date-to: inclusive range (YYYY-MM-DD).",
    )
    p.add_argument(
        "--date-to",
        type=str,
        default=None,
        help="With --date-from: inclusive range (YYYY-MM-DD).",
    )
    p.add_argument(
        "--last-years",
        type=int,
        default=None,
        metavar="N",
        help="Print scores for every daily row from today minus N years through today.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="With range mode: print JSON array instead of a terminal table.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Include raw model output, NaN counts, and monthly join key (JSON).",
    )
    p.add_argument(
        "--risk-class-mix",
        action="store_true",
        help=(
            "With --last-years or with --date-from and --date-to: print normalized "
            "risk_class / risk_class_label counts only (no per-day table)."
        ),
    )
    args = p.parse_args()

    if args.risk_class_mix:
        if args.last_years is not None:
            date_to_d = date.today()
            date_from_d = date_to_d - relativedelta(years=args.last_years)
        elif args.date_from and args.date_to:
            date_from_d = datetime.strptime(args.date_from, "%Y-%m-%d").date()
            date_to_d = datetime.strptime(args.date_to, "%Y-%m-%d").date()
        else:
            p.error("--risk-class-mix requires --last-years N or both --date-from and --date-to.")
        df_mix = infer_date_range(
            model_dir=args.model_dir,
            date_from=date_from_d,
            date_to=date_to_d,
        )
        print("risk_class (proportion of days):")
        print(df_mix["risk_class"].value_counts(normalize=True).sort_index())
        print()
        print("risk_class_label (proportion of days):")
        print(df_mix["risk_class_label"].value_counts(normalize=True))
        return

    if args.last_years is not None:
        date_to = date.today()
        date_from = date_to - relativedelta(years=args.last_years)
        df = infer_date_range(
            model_dir=args.model_dir,
            date_from=date_from,
            date_to=date_to,
        )
        if args.json:
            print(df.to_json(orient="records", indent=2))
        else:
            print(
                f"{'date':<12} {'risk_score':>10} {'cls':>4} {'band':<14} "
                f"{'src':<14}"
            )
            print("-" * 60)
            for _, row in df.iterrows():
                print(
                    f"{row['date']:<12} {row['risk_score']:>10.2f} "
                    f"{int(row['risk_class']):>4} {str(row['risk_class_label']):<14} "
                    f"{str(row['risk_class_source']):<14}"
                )
        return

    if args.date_from is not None or args.date_to is not None:
        if not args.date_from or not args.date_to:
            p.error("--date-from and --date-to must be used together.")
        date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()
        df = infer_date_range(
            model_dir=args.model_dir,
            date_from=date_from,
            date_to=date_to,
        )
        if args.json:
            print(df.to_json(orient="records", indent=2))
        else:
            print(
                f"{'date':<12} {'risk_score':>10} {'cls':>4} {'band':<14} "
                f"{'src':<14}"
            )
            print("-" * 60)
            for _, row in df.iterrows():
                print(
                    f"{row['date']:<12} {row['risk_score']:>10.2f} "
                    f"{int(row['risk_class']):>4} {str(row['risk_class_label']):<14} "
                    f"{str(row['risk_class_source']):<14}"
                )
        return

    d: date | None = None
    if args.daily_date:
        d = datetime.strptime(args.daily_date, "%Y-%m-%d").date()
    out = infer(
        model_dir=args.model_dir,
        daily_date=d,
        debug=args.debug,
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
