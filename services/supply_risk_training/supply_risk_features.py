#!/usr/bin/env python3
"""
services/supply_risk_training/supply_risk_features.py

Join dates_shrimp + months_shrimp into m__ / d__ feature columns (fixed order).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Used by ``manual_baseline_adjustment_y``; rows missing any of these are not trainable.
REQUIRED_M_COLUMNS_FOR_LABEL = (
    "m__monthly_import_zscore_6",
    "m__price_index_value",
    "m__monthly_import_roll3_std",
)

# Subset of ``m__*`` passed to the monthly RF only (fixed order). Other monthly columns from
# ``months_shrimp`` stay in the merged frame but are not model inputs.
MONTHLY_MODEL_FEATURES: tuple[str, ...] = (
    "m__monthly_import",
    "m__monthly_import_zscore_6",
    "m__monthly_import_yoy_pct",
    "m__monthly_import_mom_pct",
    "m__monthly_import_roll3_std",
    "m__price_index_value",
)


def resolve_monthly_model_feature_names(
    all_feature_names: list[str],
    *,
    raw_override: str | None = None,
) -> list[str]:
    """
    Ordered ``m__`` column names for ``rf_month``.

    Default: :data:`MONTHLY_MODEL_FEATURES`. Optional ``raw_override`` is a comma-separated
    list of ``months_shrimp`` column names *without* the ``m__`` prefix (or with ``m__``).
    """
    if raw_override:
        parts = [p.strip() for p in raw_override.split(",") if p.strip()]
        wanted: list[str] = []
        for p in parts:
            wanted.append(p if p.startswith("m__") else f"m__{p}")
    else:
        wanted = list(MONTHLY_MODEL_FEATURES)

    m_available = {c for c in all_feature_names if c.startswith("m__")}
    missing = [c for c in wanted if c not in m_available]
    if missing:
        raise ValueError(
            "Monthly model features missing from training frame: "
            f"{missing}. Available m__: {sorted(m_available)}"
        )
    return wanted


def month_anchor(dates: pd.Series, monthly_lag: str) -> pd.Series:
    """
    For each calendar day, month-start key used to join months_shrimp.date.

    monthly_lag:
      - same_month: first day of the day's calendar month
      - prev_month: first day of the previous calendar month
    """
    d = pd.to_datetime(dates)
    m0 = d.dt.to_period("M").dt.to_timestamp()
    if monthly_lag == "same_month":
        return m0
    if monthly_lag == "prev_month":
        return (m0.dt.to_period("M") - 1).dt.to_timestamp()
    raise ValueError("monthly_lag must be 'same_month' or 'prev_month'")


def build_training_frame(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    *,
    monthly_lag: str,
) -> tuple[pd.DataFrame, list[str]]:
    """
    One row per daily date with m__* and d__* columns (ordered m then d).

    Returns (frame, feature_names).
    """
    ddf = daily.copy()
    ddf["date"] = pd.to_datetime(ddf["date"])
    ddf = ddf.sort_values("date").reset_index(drop=True)
    ddf["_join_m"] = month_anchor(ddf["date"], monthly_lag)

    mdf = monthly.copy()
    mdf["date"] = pd.to_datetime(mdf["date"])
    mdf["_month_key"] = mdf["date"].dt.normalize()
    m_cols = [c for c in mdf.columns if c not in ("date", "_month_key")]
    m_feat = mdf[["_month_key"] + m_cols].copy()
    m_feat = m_feat.rename(columns={c: f"m__{c}" for c in m_cols})

    d_cols = [c for c in ddf.columns if c not in ("date", "_join_m")]
    d_part = ddf[["date", "_join_m"] + d_cols].copy()
    d_part = d_part.rename(columns={c: f"d__{c}" for c in d_cols})

    out = d_part.merge(m_feat, left_on="_join_m", right_on="_month_key", how="left")
    out = out.drop(columns=["_join_m", "_month_key"], errors="ignore")

    m_names = sorted(c for c in out.columns if c.startswith("m__"))
    d_names = sorted(c for c in out.columns if c.startswith("d__"))
    feature_names = m_names + d_names

    for c in feature_names:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    return out, feature_names


def mask_valid_monthly_rows(frame: pd.DataFrame) -> pd.Series:
    """
    ``True`` where required monthly features are present (finite), so the day can be labeled.

    Days with no matching ``months_shrimp`` row (left-merge miss) have all ``m__`` NaN and are
    ``False`` here. Partial nulls in required columns are also ``False``.
    """
    ok = pd.Series(True, index=frame.index, dtype=bool)
    for c in REQUIRED_M_COLUMNS_FOR_LABEL:
        if c not in frame.columns:
            return pd.Series(False, index=frame.index, dtype=bool)
        v = pd.to_numeric(frame[c], errors="coerce")
        arr = v.to_numpy(dtype=float)
        ok &= np.isfinite(arr)
    return ok


def describe_monthly_validation_failure(row: pd.Series, monthly_lag: str) -> str:
    """Short diagnostic for infer / train when required ``m__`` fields are missing."""
    mk = month_anchor(pd.Series([row["date"]]), monthly_lag).iloc[0]
    if hasattr(mk, "date"):
        mk_s = mk.date().isoformat()
    elif hasattr(mk, "isoformat"):
        mk_s = str(mk.isoformat())[:10]
    else:
        mk_s = str(mk)
    parts: list[str] = [f"join month (month-start): {mk_s}"]
    for c in REQUIRED_M_COLUMNS_FOR_LABEL:
        if c not in row.index:
            parts.append(f"{c}: absent")
            continue
        val = pd.to_numeric(row[c], errors="coerce")
        try:
            ok = bool(np.isfinite(float(val)))
        except (TypeError, ValueError):
            ok = False
        if not ok:
            parts.append(f"{c}: missing or non-finite")
    return "; ".join(parts)


def build_monthly_feature_table(monthly: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    One row per month-start in ``months_shrimp`` with ``m__`` columns and ``ym`` (YYYY-MM).

    Used for inspection or joins; decomposed training builds month targets from the daily frame.
    """
    mdf = monthly.copy()
    mdf["date"] = pd.to_datetime(mdf["date"])
    mdf["_month_key"] = mdf["date"].dt.normalize()
    m_cols = [c for c in mdf.columns if c not in ("date", "_month_key")]
    m_feat = mdf[["_month_key"] + m_cols].copy()
    m_feat = m_feat.rename(columns={c: f"m__{c}" for c in m_cols})
    m_feat["ym"] = m_feat["_month_key"].dt.strftime("%Y-%m")
    m_names = sorted(c for c in m_feat.columns if c.startswith("m__"))
    for c in m_names:
        m_feat[c] = pd.to_numeric(m_feat[c], errors="coerce")
    out = m_feat.drop(columns=["_month_key"], errors="ignore")
    return out, m_names


def train_validation_masks_by_month(
    day_dates: pd.Series,
    holdout_months: int,
) -> tuple[pd.Series, pd.Series]:
    """Last holdout_months calendar months are validation; boolean masks."""
    d = pd.to_datetime(day_dates)
    periods = d.dt.to_period("M")
    uniq = periods.drop_duplicates().sort_values()
    n = len(uniq)
    if holdout_months <= 0:
        raise ValueError("holdout_months must be >= 1")
    if holdout_months >= n:
        raise ValueError(
            f"holdout_months ({holdout_months}) must be smaller than distinct months ({n})"
        )
    val_set = set(uniq.iloc[-holdout_months:])
    val_mask = periods.isin(val_set)
    train_mask = ~val_mask
    return train_mask, val_mask
