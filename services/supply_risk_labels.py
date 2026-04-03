#!/usr/bin/env python3
"""
services/supply_risk_labels.py

Proxy supply-risk labels from months_shrimp only (z-score + price index).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LABEL_FORMULA_V1 = (
    "raw = 8*relu(-zscore_6) + 0.15*relu(price_index - p_ref); "
    "y = 100*(raw-raw_min)/(raw_max-raw_min) clipped, fit raw_min/max on train months only"
)

DEFAULT_P_REF = 90.0
SHORTAGE_WEIGHT = 8.0
PRICE_WEIGHT = 0.15
SCALE_EPS = 1e-9


def monthly_raw_stress(
    months: pd.DataFrame,
    *,
    p_ref: float = DEFAULT_P_REF,
    shortage_weight: float = SHORTAGE_WEIGHT,
    price_weight: float = PRICE_WEIGHT,
) -> pd.Series:
    """
    One raw stress scalar per monthly row (index = month-start Timestamp).
    Higher = more stress (weak imports + high price index vs p_ref).
    """
    z = pd.to_numeric(months["monthly_import_zscore_6"], errors="coerce").astype(float)
    p = pd.to_numeric(months["price_index_value"], errors="coerce").astype(float)
    shortage = np.maximum(0.0, -z) * shortage_weight
    price_up = np.maximum(0.0, p - p_ref) * price_weight
    raw = shortage + price_up
    idx = pd.to_datetime(months["date"]).dt.to_period("M").dt.to_timestamp()
    return pd.Series(raw.values, index=idx, name="raw")


def minmax_scale_to_100(
    raw: pd.Series,
    *,
    ref_min: float | None = None,
    ref_max: float | None = None,
) -> pd.Series:
    """Map raw stress to [0, 100] using min-max; optional fixed ref range (train-only)."""
    if ref_min is None:
        ref_min = float(np.nanmin(raw.to_numpy()))
    if ref_max is None:
        ref_max = float(np.nanmax(raw.to_numpy()))
    denom = ref_max - ref_min + SCALE_EPS
    scaled = 100.0 * (raw.astype(float) - ref_min) / denom
    return scaled.clip(0.0, 100.0)


def _month_starts(dates: pd.Series) -> pd.Series:
    return pd.to_datetime(dates).dt.to_period("M").dt.to_timestamp()


def fit_label_scaling_from_train_months(
    raw_by_month_start: pd.Series,
    train_day_dates: pd.Series,
) -> tuple[float, float]:
    """Min/max of raw stress only on months that appear in the training day set."""
    m_starts = _month_starts(train_day_dates)
    months_in_train = pd.Index(np.sort(np.unique(m_starts.astype("datetime64[ns]"))))
    aligned = raw_by_month_start.reindex(months_in_train).dropna()
    if aligned.empty:
        raise ValueError("No overlapping monthly raw values for train months.")
    return float(aligned.min()), float(aligned.max())


def monthly_scaled_labels(
    months: pd.DataFrame,
    train_day_dates: pd.Series,
    *,
    p_ref: float = DEFAULT_P_REF,
) -> pd.Series:
    """
    y_month indexed by month-start Timestamp, scaled 0–100 using train-only min/max on raw.
    """
    raw = monthly_raw_stress(months, p_ref=p_ref)
    rmin, rmax = fit_label_scaling_from_train_months(raw, train_day_dates)
    return minmax_scale_to_100(raw, ref_min=rmin, ref_max=rmax)


def attach_labels_to_days(
    day_dates: pd.Series,
    y_by_month_start: pd.Series,
    *,
    label_month: str,
) -> pd.Series:
    """
    label_month:
      - 'same': day in M gets y(M)
      - 'next': day in M gets y(M+1)
    """
    d = pd.to_datetime(day_dates)
    m0 = d.dt.to_period("M").dt.to_timestamp()
    if label_month == "same":
        key = m0
    elif label_month == "next":
        key = (m0.dt.to_period("M") + 1).dt.to_timestamp()
    else:
        raise ValueError("label_month must be 'same' or 'next'")
    yvals = y_by_month_start.reindex(key.to_numpy()).to_numpy()
    return pd.Series(yvals, index=d, name="y")
