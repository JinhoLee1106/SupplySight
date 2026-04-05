#!/usr/bin/env python3
"""
services/supply_risk_training/supply_risk_labels.py

Monthly proxy from months_shrimp (z-score + price index), plus optional daily oil/sentiment bump.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .baseline_risk_tables import BASELINE_RISK_BY_YM

LABEL_FORMULA_V1 = (
    "a=relu(-zscore_6), b=relu(price_index-p_ref); "
    "raw = w_shortage*a + w_price*b; "
    "w_shortage,w_price = IQR-balanced on train months: inverse IQR(a),inverse IQR(b), normalized to sum 1; "
    "fallback if insufficient train months: normalize legacy (8,0.15); "
    "p_ref = median(price_index_value) over months_shrimp; "
    "y_month = y_min + (100-y_min)*(raw-raw_min)/(raw_max-raw_min) clipped to [y_min,100], "
    "fit raw_min/max on train months only; "
    "y = clip(y_month + bump_oil_sent, y_min, 100) per day; "
    "bump_oil_sent = train-calibrated robust z-mix of d__oil_price and d__sentiment_score "
    "(mapped to ±12); d__oil_price and d__sentiment_score excluded from RF X to limit leakage"
)

LABEL_FORMULA_MANUAL = (
    "y = clip(baseline_risk[YYYY-MM] + adjustment, 1, 100); "
    "baseline_risk = fixed monthly table; "
    "shortage = relu(-z), price_stress = relu(P - P_ref), vol = m__monthly_import_roll3_std; "
    "oil = d__oil_price, sentiment = d__sentiment_score (filled with train median before norm); "
    "P_ref = median(P) on train rows; each signal train min/max normalized to ~[0,1]; "
    "adjustment = 20 * (0.35*s + 0.25*p + 0.15*v + 0.125*oil + 0.125*sent - 0.5)"
)

# Weights for manual label mix (must sum to 1).
ADJ_MIX_W_SHORTAGE = 0.35
ADJ_MIX_W_PRICE = 0.25
ADJ_MIX_W_VOL = 0.15
ADJ_MIX_W_OIL = 0.125
ADJ_MIX_W_SENTIMENT = 0.125

MANUAL_RISK_MIN = 1.0
MANUAL_RISK_MAX = 100.0

# Decomposed model: clip daily delta before adding to monthly risk (matches ~±10 manual scale).
DELTA_CLIP_DEFAULT = 15.0

# Columns used in bump_oil_sent; omit from predictors for the same target.
LABEL_LEAKAGE_EXCLUDE_D = frozenset({"d__oil_price", "d__sentiment_score"})

OIL_SENTIMENT_LABEL_MAX_ABS_BUMP = 12.0
OIL_LABEL_WEIGHT = 0.5
SENTIMENT_LABEL_WEIGHT = 0.5

# Lowest scaled label (was 0). Training with many y=0 teaches RF to predict 0 for “low stress”
# feature patterns; a small floor spreads the low end and reduces spurious 0.0 scores at inference.
LABEL_SCORE_MIN = 5.0
LABEL_SCORE_MAX = 100.0

# Ordinal bands for the continuous risk score (compare alongside linear model output).
RISK_CLASS_LABELS: tuple[str, ...] = (
    "low",
    "average",
    "high",
)


def risk_bucket(x: float) -> int:
    """
    Map continuous risk (typically 1–100) to class ``0``..``2``.

    **low** ``< 40``, **average** ``[40, 60]``, **high** ``> 60`` (up to :data:`LABEL_SCORE_MAX`).
    """
    if x < 40:
        return 0
    if x <= 60:
        return 1
    return 2


def risk_class_from_scores(scores: np.ndarray | pd.Series) -> np.ndarray:
    """Vectorized :func:`risk_bucket` for arrays or Series."""
    s = np.asarray(scores, dtype=float)
    return np.select([s < 40, s <= 60], [0, 1], default=2).astype(np.int64)


def risk_class_label(code: int) -> str:
    if 0 <= code <= 2:
        return RISK_CLASS_LABELS[code]
    raise ValueError(f"risk_class must be 0..2, got {code!r}")


DEFAULT_P_REF = 90.0  # fallback for tests / callers that pass p_ref explicitly
# Default only for direct monthly_raw_stress() calls; monthly_scaled_labels uses IQR-balanced weights.
SHORTAGE_WEIGHT = 8.0
PRICE_WEIGHT = 0.15
SCALE_EPS = 1e-9


def median_p_ref(months: pd.DataFrame) -> float:
    """Price reference = median of ``price_index_value`` in monthly data (finite values only)."""
    if "price_index_value" not in months.columns:
        raise ValueError("months_shrimp must include price_index_value.")
    prices = pd.to_numeric(months["price_index_value"], errors="coerce").dropna()
    if prices.empty:
        raise ValueError("Cannot set p_ref: no finite price_index_value in months_shrimp.")
    return float(prices.median())


def _strip_tz_series(ser: pd.Series) -> pd.Series:
    d = pd.to_datetime(ser, utc=False)
    if getattr(d.dt, "tz", None) is not None:
        return d.dt.tz_convert(None)
    return d


def _strip_tz_datetime_index(idx: pd.Index) -> pd.DatetimeIndex:
    d = pd.DatetimeIndex(pd.to_datetime(idx))
    if d.tz is not None:
        return d.tz_convert("UTC").tz_localize(None)
    return d


def _ym_keys_from_datetime_index(idx: pd.Index) -> pd.Index:
    """Stable 'YYYY-MM' labels for calendar months (avoids Period/str quirks)."""
    d = _strip_tz_datetime_index(idx)
    return pd.Index(d.strftime("%Y-%m"))


def y_mean_by_label_month(
    label_ym: pd.Series, y: pd.Series, train_mask: pd.Series
) -> pd.Series:
    """
    Mean ``y`` per ``label_ym`` over rows where ``train_mask`` is True.
    Index = ``YYYY-MM`` strings.
    """
    m = train_mask.to_numpy(dtype=bool)
    sub = pd.DataFrame({"label_ym": label_ym[m], "y": y[m]})
    return sub.groupby("label_ym", sort=False)["y"].mean()


def label_month_key_series(day_dates: pd.Series, *, label_month: str) -> pd.Series:
    """Per-row ``YYYY-MM`` key for the label month (``same`` or ``next`` calendar month)."""
    keys = _ym_keys_from_day_series(day_dates, label_month=label_month)
    return pd.Series(keys, index=day_dates.index, dtype=str, name="label_ym")


def _ym_keys_from_day_series(day_dates: pd.Series, *, label_month: str) -> np.ndarray:
    """One 'YYYY-MM' per row: label month (same as calendar month of day, or next)."""
    d = _strip_tz_series(day_dates)
    p = d.dt.to_period("M")
    if label_month == "next":
        p = p + 1
    elif label_month != "same":
        raise ValueError("label_month must be 'same' or 'next'")
    # Period -> month-start Timestamp -> uniform %Y-%m
    ts = p.dt.to_timestamp(how="start")
    return ts.dt.strftime("%Y-%m").to_numpy()


def _period_str_lookup_from_days(day_dates: pd.Series, *, label_month: str) -> np.ndarray:
    """Deprecated name; use _ym_keys_from_day_series."""
    return _ym_keys_from_day_series(day_dates, label_month=label_month)


def explain_label_failure(
    day_dates: pd.Series,
    y_month: pd.Series,
    *,
    label_month: str,
) -> str:
    """Human-readable stats when attach_labels_to_days yields all NaN."""
    lk = _ym_keys_from_day_series(day_dates, label_month=label_month)
    mk = _ym_keys_from_datetime_index(y_month.index)
    mapper = pd.Series(y_month.to_numpy(), index=mk)
    if mapper.index.duplicated().any():
        mapper = mapper.groupby(level=0).first()
    idx_set = set(mapper.index.astype(str))
    lk_arr = np.asarray(lk, dtype=object)
    present = np.array([str(x) in idx_set for x in lk_arr], dtype=bool)
    n_key_missing = int((~present).sum())
    aligned = mapper.reindex(lk_arr)
    n_val_nan = int(np.sum(present & aligned.isna().to_numpy()))
    finite_ym = int(np.isfinite(y_month.to_numpy(dtype=float)).sum())
    parts = [
        f"y_month finite values: {finite_ym} / {len(y_month)}",
        f"day rows: {len(lk)}; lookup keys missing from monthly label index: {n_key_missing}",
        f"keys present but scaled label NaN (often NULL zscore/price in months_shrimp): {n_val_nan}",
        f"sample label months: {list(mapper.index[:8])}",
        f"sample day months needed: {list(pd.unique(lk_arr)[:8])}",
    ]
    return "\n".join(parts)


def _shortage_price_terms_unweighted(months: pd.DataFrame, p_ref: float) -> tuple[pd.Series, pd.Series]:
    """``a = relu(-z)``, ``b = relu(price - p_ref)`` per month-start index."""
    z = pd.to_numeric(months["monthly_import_zscore_6"], errors="coerce").astype(float)
    p = pd.to_numeric(months["price_index_value"], errors="coerce").astype(float)
    a = np.maximum(0.0, -z.to_numpy(dtype=float))
    b = np.maximum(0.0, (p - p_ref).to_numpy(dtype=float))
    dt = _strip_tz_series(months["date"])
    idx = dt.dt.to_period("M").dt.to_timestamp()
    return (
        pd.Series(a, index=idx, name="shortage"),
        pd.Series(b, index=idx, name="price_up"),
    )


def fit_iqr_balanced_shortage_price_weights(
    months: pd.DataFrame,
    train_day_dates: pd.Series,
    p_ref: float,
) -> tuple[float, float, dict[str, float | str]]:
    """
    Weights inversely proportional to IQR of ``a`` and ``b`` on **train** calendar months,
    normalized to sum to 1. Reduces dominance of whichever channel has larger historical spread.
    """
    train_m = _ym_keys_from_day_series(train_day_dates, label_month="same")
    train_keys = np.sort(np.unique(train_m))

    a_ser, b_ser = _shortage_price_terms_unweighted(months, p_ref)
    ak = _ym_keys_from_datetime_index(a_ser.index)
    a_by_key = pd.Series(a_ser.to_numpy(), index=ak)
    b_by_key = pd.Series(b_ser.to_numpy(), index=ak)
    if a_by_key.index.duplicated().any():
        a_by_key = a_by_key.groupby(level=0).first()
        b_by_key = b_by_key.groupby(level=0).first()

    a_al = a_by_key.reindex(train_keys)
    b_al = b_by_key.reindex(train_keys)
    mask = a_al.notna() & b_al.notna()
    a_tr = a_al[mask].to_numpy(dtype=float)
    b_tr = b_al[mask].to_numpy(dtype=float)

    def _iqr(x: np.ndarray) -> float:
        if len(x) < 2:
            return 0.0
        return float(np.percentile(x, 75) - np.percentile(x, 25))

    iqr_a = _iqr(a_tr)
    iqr_b = _iqr(b_tr)

    legacy_sum = SHORTAGE_WEIGHT + PRICE_WEIGHT
    fallback_w_s = SHORTAGE_WEIGHT / legacy_sum
    fallback_w_p = PRICE_WEIGHT / legacy_sum

    if len(a_tr) < 2:
        return (
            fallback_w_s,
            fallback_w_p,
            {
                "method": "fallback_legacy_ratio",
                "reason": "fewer_than_2_train_months",
                "iqr_shortage": iqr_a,
                "iqr_price": iqr_b,
                "w_shortage": fallback_w_s,
                "w_price": fallback_w_p,
            },
        )

    inv_a = 1.0 / (iqr_a + SCALE_EPS)
    inv_b = 1.0 / (iqr_b + SCALE_EPS)
    s = inv_a + inv_b
    w_s = inv_a / s
    w_p = inv_b / s

    meta: dict[str, float | str] = {
        "method": "iqr_balanced",
        "iqr_shortage": iqr_a,
        "iqr_price": iqr_b,
        "w_shortage": w_s,
        "w_price": w_p,
    }
    return w_s, w_p, meta


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
    a_ser, b_ser = _shortage_price_terms_unweighted(months, p_ref)
    raw = a_ser.to_numpy(dtype=float) * shortage_weight + b_ser.to_numpy(dtype=float) * price_weight
    return pd.Series(raw, index=a_ser.index, name="raw")


def minmax_scale_to_100(
    raw: pd.Series,
    *,
    ref_min: float | None = None,
    ref_max: float | None = None,
    score_min: float = LABEL_SCORE_MIN,
    score_max: float = LABEL_SCORE_MAX,
) -> pd.Series:
    """Map raw stress to ``[score_min, score_max]`` using min-max; ref range is train-only."""
    if ref_min is None:
        ref_min = float(np.nanmin(raw.to_numpy()))
    if ref_max is None:
        ref_max = float(np.nanmax(raw.to_numpy()))
    denom = ref_max - ref_min + SCALE_EPS
    t = (raw.astype(float) - ref_min) / denom
    scaled = score_min + (score_max - score_min) * t
    return scaled.clip(score_min, score_max)


def fit_label_scaling_from_train_months(
    raw_by_month_start: pd.Series,
    train_day_dates: pd.Series,
) -> tuple[float, float]:
    """Min/max of raw stress only on months that appear in the training day set."""
    train_m = _ym_keys_from_day_series(train_day_dates, label_month="same")
    train_keys = np.sort(np.unique(train_m))

    raw_keys = _ym_keys_from_datetime_index(raw_by_month_start.index)
    raw_by_key = pd.Series(raw_by_month_start.to_numpy(), index=raw_keys)
    if raw_by_key.index.duplicated().any():
        raw_by_key = raw_by_key.groupby(level=0).first()
    aligned = raw_by_key.reindex(train_keys).dropna()
    if aligned.empty:
        raise ValueError("No overlapping monthly raw values for train months.")
    return float(aligned.min()), float(aligned.max())


def monthly_scaled_labels(
    months: pd.DataFrame,
    train_day_dates: pd.Series,
    *,
    p_ref: float = DEFAULT_P_REF,
) -> tuple[pd.Series, dict[str, float | str]]:
    """
    y_month indexed by month-start Timestamp, scaled to [LABEL_SCORE_MIN, 100] using train-only
    min/max on raw. Raw uses IQR-balanced shortage/price weights fit on train months.

    Returns ``(y_month_series, weight_meta)``.
    """
    w_s, w_p, wmeta = fit_iqr_balanced_shortage_price_weights(
        months, train_day_dates, p_ref
    )
    raw = monthly_raw_stress(months, p_ref=p_ref, shortage_weight=w_s, price_weight=w_p)
    rmin, rmax = fit_label_scaling_from_train_months(raw, train_day_dates)
    scaled = minmax_scale_to_100(raw, ref_min=rmin, ref_max=rmax)
    return scaled, wmeta


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

    Lookup uses YYYY-MM strings so Postgres tz-aware vs naive timestamps cannot
    break alignment with the monthly label series.
    """
    d = _strip_tz_series(day_dates)
    lookup_str = _ym_keys_from_day_series(day_dates, label_month=label_month)

    label_keys = _ym_keys_from_datetime_index(y_by_month_start.index)
    mapper = pd.Series(y_by_month_start.to_numpy(), index=label_keys)
    if mapper.index.duplicated().any():
        mapper = mapper.groupby(level=0).first()

    yvals = mapper.reindex(lookup_str).to_numpy()
    return pd.Series(yvals, index=d, name="y")


def oil_sentiment_label_bump(
    frame: pd.DataFrame,
    train_fit_mask: pd.Series,
    *,
    max_abs_bump: float = OIL_SENTIMENT_LABEL_MAX_ABS_BUMP,
) -> tuple[np.ndarray, dict[str, float | bool | str]]:
    """
    Daily adjustment from ``d__oil_price`` and ``d__sentiment_score``.

    Train-only medians/IQR; missing filled with train medians before z-scoring.
    Maps weighted z-scores to ``[-max_abs_bump, max_abs_bump]`` using train 5th–95th percentiles
    of the mix on ``train_fit_mask``.

    If columns are missing, returns zeros and ``enabled: False``.
    """
    n = len(frame)
    if "d__oil_price" not in frame.columns or "d__sentiment_score" not in frame.columns:
        return np.zeros(n, dtype=float), {"enabled": False}

    oil = pd.to_numeric(frame["d__oil_price"], errors="coerce").to_numpy(dtype=float)
    sent = pd.to_numeric(frame["d__sentiment_score"], errors="coerce").to_numpy(dtype=float)
    mask = train_fit_mask.to_numpy(dtype=bool)

    def _train_finite(a: np.ndarray) -> np.ndarray:
        return a[mask & np.isfinite(a)]

    o_tr = _train_finite(oil)
    s_tr = _train_finite(sent)
    med_oil = float(np.median(o_tr)) if len(o_tr) else 0.0
    med_sent = float(np.median(s_tr)) if len(s_tr) else 0.0

    def _iqr(a: np.ndarray) -> float:
        if len(a) < 2:
            return 1.0
        q75, q25 = np.percentile(a, [75, 25])
        return float(q75 - q25) + SCALE_EPS

    iqr_oil = _iqr(o_tr) if len(o_tr) else 1.0
    iqr_sent = _iqr(s_tr) if len(s_tr) else 1.0

    oil_f = np.where(np.isfinite(oil), oil, med_oil)
    sent_f = np.where(np.isfinite(sent), sent, med_sent)

    zo = np.clip((oil_f - med_oil) / iqr_oil, -3.0, 3.0)
    zs = np.clip((sent_f - med_sent) / iqr_sent, -3.0, 3.0)
    mix = OIL_LABEL_WEIGHT * zo + SENTIMENT_LABEL_WEIGHT * zs

    tr_mix = mix[mask]
    tr_mix = tr_mix[np.isfinite(tr_mix)]
    if len(tr_mix) == 0:
        return np.zeros(n, dtype=float), {
            "enabled": True,
            "max_abs_bump": max_abs_bump,
            "note": "empty_train_mix",
        }

    lo, hi = np.percentile(tr_mix, [5.0, 95.0])
    span = max(hi - lo, 1e-9)
    mid = 0.5 * (lo + hi)
    bump = (mix - mid) / span * max_abs_bump
    bump = np.clip(bump, -max_abs_bump, max_abs_bump)

    meta: dict[str, float | bool | str] = {
        "enabled": True,
        "max_abs_bump": max_abs_bump,
        "oil_median": med_oil,
        "oil_iqr": iqr_oil,
        "sentiment_median": med_sent,
        "sentiment_iqr": iqr_sent,
        "mix_p5": float(lo),
        "mix_p95": float(hi),
    }
    return bump, meta


def _normalize_train_minmax(s: pd.Series, train_mask: pd.Series) -> pd.Series:
    """``(x - min_train) / (max_train - min_train + eps)`` per column."""
    tr = s.loc[train_mask]
    arr = tr.to_numpy(dtype=float)
    finite = np.isfinite(arr)
    if not finite.any():
        return pd.Series(0.0, index=s.index, dtype=float)
    lo = float(np.nanmin(arr[finite]))
    hi = float(np.nanmax(arr[finite]))
    denom = hi - lo + 1e-6
    return (s - lo) / denom


def _optional_float_col(frame: pd.DataFrame, name: str) -> pd.Series:
    """Column as float; all-NaN if missing."""
    if name not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce")


def _fill_train_median(s: pd.Series, train_mask: pd.Series) -> pd.Series:
    """Impute NaN with median of finite train values (else 0)."""
    tr = pd.to_numeric(s.loc[train_mask], errors="coerce")
    arr = tr.to_numpy(dtype=float)
    finite = arr[np.isfinite(arr)]
    med = float(np.median(finite)) if len(finite) else 0.0
    return pd.to_numeric(s, errors="coerce").fillna(med)


def build_oil_sentiment_formula_meta(
    frame: pd.DataFrame, train_mask: pd.Series
) -> dict[str, Any]:
    """
    Train-time bounds for ``d__oil_price`` and ``d__sentiment_score`` (filled, then min/max
    on train rows) — same normalization idea as ``manual_baseline_adjustment_y``, but only the
    daily columns needed for a fixed adjustment on top of learned monthly risk.
    """
    train_mask = train_mask.astype(bool)
    oil_s = _fill_train_median(_optional_float_col(frame, "d__oil_price"), train_mask)
    sent_s = _fill_train_median(_optional_float_col(frame, "d__sentiment_score"), train_mask)

    def _bounds(s: pd.Series) -> tuple[float, float, float]:
        tr = pd.to_numeric(s.loc[train_mask], errors="coerce")
        arr = tr.to_numpy(dtype=float)
        fin = arr[np.isfinite(arr)]
        if len(fin) == 0:
            return 0.0, 1.0, 0.0
        lo, hi = float(np.nanmin(fin)), float(np.nanmax(fin))
        med = float(np.median(fin))
        return lo, hi, med

    o_lo, o_hi, o_med = _bounds(oil_s)
    s_lo, s_hi, s_med = _bounds(sent_s)
    return {
        "kind": "oil_sentiment_train_minmax",
        "oil_lo": o_lo,
        "oil_hi": o_hi,
        "oil_med": o_med,
        "sent_lo": s_lo,
        "sent_hi": s_hi,
        "sent_med": s_med,
        "w_oil": ADJ_MIX_W_OIL,
        "w_sent": ADJ_MIX_W_SENTIMENT,
        "adjustment_scale": 20.0,
    }


def daily_adjustment_oil_sentiment_batch(
    d_block: np.ndarray,
    formula_meta: dict[str, Any],
    d_oil_ix: int | None,
    d_sent_ix: int | None,
    *,
    delta_clip: float,
) -> np.ndarray:
    """
    Deterministic daily adjustment from oil + sentiment only:

    ``delta = scale * (w_oil * oil_n + w_sent * sent_n - (w_oil + w_sent) * 0.5)``

    with ``oil_n``, ``sent_n`` in ``[0, 1]`` from train min–max; missing column → neutral ``0.5``.
    Then clip to ``[-delta_clip, +delta_clip]``.
    """
    n = int(d_block.shape[0])
    m = formula_meta
    w_o = float(m["w_oil"])
    w_s = float(m["w_sent"])
    scale = float(m.get("adjustment_scale", 20.0))

    def _norm_col(
        ix: int | None, lo: float, hi: float, med: float
    ) -> np.ndarray:
        if ix is None:
            return np.full(n, 0.5, dtype=float)
        v = d_block[:, ix].astype(float)
        v = np.where(np.isfinite(v), v, med)
        denom = hi - lo + 1e-6
        vn = (v - lo) / denom
        return np.clip(vn, 0.0, 1.0)

    oil_n = _norm_col(d_oil_ix, float(m["oil_lo"]), float(m["oil_hi"]), float(m["oil_med"]))
    sent_n = _norm_col(
        d_sent_ix, float(m["sent_lo"]), float(m["sent_hi"]), float(m["sent_med"])
    )
    delta = scale * (w_o * oil_n + w_s * sent_n - (w_o + w_s) * 0.5)
    return np.clip(delta, -float(delta_clip), float(delta_clip))


def manual_baseline_adjustment_y(
    frame: pd.DataFrame,
    train_mask: pd.Series,
    *,
    label_month: str,
) -> tuple[pd.Series, dict[str, Any]]:
    """
    Expert monthly baseline (:data:`BASELINE_RISK_BY_YM` in ``baseline_risk_tables``) plus dynamic
    adjustment from shortage, price stress, import volatility, oil price, and sentiment
    (train-normalized).

    The returned ``y`` is the **only** supervised target for supply-risk training: the monthly
    linear head regresses mean ``y`` per month, and the monthly classifier uses
    ``risk_bucket(y)`` (per day, aggregated to a month-level mode). Both use this same series.
    """
    keys = _ym_keys_from_day_series(frame["date"], label_month=label_month)
    baseline = np.array(
        [BASELINE_RISK_BY_YM.get(str(k), np.nan) for k in keys], dtype=float
    )

    z = pd.to_numeric(frame["m__monthly_import_zscore_6"], errors="coerce")
    P = pd.to_numeric(frame["m__price_index_value"], errors="coerce")
    vol = pd.to_numeric(frame["m__monthly_import_roll3_std"], errors="coerce")

    p_ref = float(np.nanmedian(P.loc[train_mask].to_numpy(dtype=float)))

    shortage = np.maximum(0.0, -z.to_numpy(dtype=float))
    price_stress = np.maximum(0.0, P.to_numpy(dtype=float) - p_ref)
    volatility = vol.to_numpy(dtype=float)

    s_ser = pd.Series(shortage, index=frame.index)
    p_ser = pd.Series(price_stress, index=frame.index)
    v_ser = pd.Series(volatility, index=frame.index)

    s_n = _normalize_train_minmax(s_ser, train_mask)
    p_n = _normalize_train_minmax(p_ser, train_mask)
    v_n = _normalize_train_minmax(v_ser, train_mask)

    oil_s = _fill_train_median(_optional_float_col(frame, "d__oil_price"), train_mask)
    sent_s = _fill_train_median(_optional_float_col(frame, "d__sentiment_score"), train_mask)
    oil_n = _normalize_train_minmax(oil_s, train_mask)
    sent_n = _normalize_train_minmax(sent_s, train_mask)

    mix = (
        ADJ_MIX_W_SHORTAGE * s_n
        + ADJ_MIX_W_PRICE * p_n
        + ADJ_MIX_W_VOL * v_n
        + ADJ_MIX_W_OIL * oil_n
        + ADJ_MIX_W_SENTIMENT * sent_n
    )
    adjustment = 20.0 * (mix - 0.5)
    adj_arr = adjustment.to_numpy(dtype=float)
    y = np.clip(baseline + adj_arr, MANUAL_RISK_MIN, MANUAL_RISK_MAX)
    y = np.where(np.isfinite(baseline), y, np.nan)

    meta: dict[str, Any] = {
        "p_ref_train_median": p_ref,
        "weights": {
            "shortage": ADJ_MIX_W_SHORTAGE,
            "price_stress": ADJ_MIX_W_PRICE,
            "volatility": ADJ_MIX_W_VOL,
            "oil": ADJ_MIX_W_OIL,
            "sentiment": ADJ_MIX_W_SENTIMENT,
        },
        "adjustment_scale": 20.0,
        "clip": [MANUAL_RISK_MIN, MANUAL_RISK_MAX],
    }
    return pd.Series(y, index=frame.index, name="y"), meta
