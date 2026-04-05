#!/usr/bin/env python3
"""
services/supply_risk_features.py

Join dates_shrimp + months_shrimp into m__ / d__ feature columns (fixed order).
"""
from __future__ import annotations

import pandas as pd


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
