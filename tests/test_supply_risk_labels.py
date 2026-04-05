# tests/test_supply_risk_labels.py

from __future__ import annotations

import pandas as pd

import numpy as np

from services.supply_risk_training.supply_risk_labels import (
    BASELINE_RISK_BY_YM,
    LABEL_SCORE_MIN,
    MANUAL_RISK_MAX,
    MANUAL_RISK_MIN,
    attach_labels_to_days,
    fit_iqr_balanced_shortage_price_weights,
    manual_baseline_adjustment_y,
    median_p_ref,
    minmax_scale_to_100,
    monthly_raw_stress,
    monthly_scaled_labels,
    oil_sentiment_label_bump,
    risk_bucket,
    risk_class_from_scores,
)


def test_manual_baseline_adjustment_y_clip_and_baseline() -> None:
    """Toy frame: same calendar month + identical m__ rows → same y; bounds and p_ref."""
    idx = pd.RangeIndex(2)
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-10", "2024-01-11"]),
            "m__monthly_import_zscore_6": [0.0, 0.0],
            "m__price_index_value": [90.0, 90.0],
            "m__monthly_import_roll3_std": [1.0, 1.0],
            "d__oil_price": [70.0, 70.0],
            "d__sentiment_score": [0.0, 0.0],
        },
        index=idx,
    )
    train_mask = pd.Series([True, True], index=idx)
    y, meta = manual_baseline_adjustment_y(frame, train_mask, label_month="same")
    assert meta["p_ref_train_median"] == 90.0
    assert float(y.iloc[0]) == float(y.iloc[1])
    bl = BASELINE_RISK_BY_YM["2024-01"]
    # Constant train features → normalized mix 0 → adjustment = 20*(0-0.5) = -10
    assert abs(float(y.iloc[0]) - (bl - 10.0)) < 1e-6
    assert (y >= MANUAL_RISK_MIN).all() and (y <= MANUAL_RISK_MAX).all()


def test_oil_sentiment_bump_enabled() -> None:
    frame = pd.DataFrame(
        {
            "d__oil_price": [70.0, 75.0, 80.0],
            "d__sentiment_score": [-1.0, 0.0, 1.0],
        }
    )
    train_fit = pd.Series([True, True, False])
    bump, meta = oil_sentiment_label_bump(frame, train_fit)
    assert meta["enabled"] is True
    assert len(bump) == 3


def test_iqr_balanced_weights_sum_to_one() -> None:
    months = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "monthly_import_zscore_6": [-2.0, 0.5, -1.0],
            "price_index_value": [90.0, 92.0, 88.0],
        }
    )
    train_days = pd.Series(
        pd.to_datetime(["2024-01-10", "2024-02-11", "2024-03-05"])
    )
    w_s, w_p, meta = fit_iqr_balanced_shortage_price_weights(months, train_days, 90.0)
    assert abs(w_s + w_p - 1.0) < 1e-9
    assert meta["method"] == "iqr_balanced"
    assert abs(meta["w_shortage"] + meta["w_price"] - 1.0) < 1e-9


def test_minmax_scaled_uses_score_floor() -> None:
    raw = pd.Series([0.0, 10.0], dtype=float)
    y = minmax_scale_to_100(raw, ref_min=0.0, ref_max=10.0)
    assert abs(float(y.iloc[0]) - LABEL_SCORE_MIN) < 1e-6
    assert abs(float(y.iloc[1]) - 100.0) < 1e-6


def test_median_p_ref() -> None:
    months = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01"],
            "monthly_import_zscore_6": [0.0, 0.0],
            "price_index_value": [80.0, 100.0],
        }
    )
    assert median_p_ref(months) == 90.0


def test_monthly_raw_stress_increases_with_price() -> None:
    months = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01"],
            "monthly_import_zscore_6": [0.0, 0.0],
            "price_index_value": [85.0, 100.0],
        }
    )
    raw = monthly_raw_stress(months, p_ref=90.0)
    assert raw.iloc[0] < raw.iloc[1]


def test_labels_same_vs_next() -> None:
    months = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "monthly_import_zscore_6": [-1.0, 1.0, -0.5],
            "price_index_value": [95.0, 88.0, 96.0],
        }
    )
    # Train scaling uses Jan+Feb so raw min/max spans distinct months.
    train_days = pd.Series(pd.to_datetime(["2024-01-10", "2024-02-11"]))
    y_m, _ = monthly_scaled_labels(months, train_days, p_ref=90.0)
    y_same = attach_labels_to_days(
        pd.Series(pd.to_datetime(["2024-01-15"])), y_m, label_month="same"
    )
    y_next = attach_labels_to_days(
        pd.Series(pd.to_datetime(["2024-01-15"])), y_m, label_month="next"
    )
    assert y_same.notna().all() and y_next.notna().all()
    assert float(y_same.iloc[0]) != float(y_next.iloc[0])


def test_attach_labels_uses_calendar_month_not_row_index() -> None:
    """Regression: labels must match Period values, not default 0..n row index."""
    months = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01"],
            "monthly_import_zscore_6": [0.0, 0.0],
            "price_index_value": [90.0, 90.0],
        }
    )
    train_days = pd.Series(pd.to_datetime(["2024-01-05", "2024-02-05"]))
    y_m, _ = monthly_scaled_labels(months, train_days, p_ref=90.0)
    day_dates = pd.Series(
        pd.to_datetime(["2024-01-15", "2024-02-20"]),
        index=[100, 200],
    )
    y = attach_labels_to_days(day_dates, y_m, label_month="same")
    assert y.notna().all() and len(y) == 2


def test_risk_bucket_and_vectorized() -> None:
    assert risk_bucket(0.0) == 0
    assert risk_bucket(39.99) == 0
    assert risk_bucket(40.0) == 1
    assert risk_bucket(59.99) == 1
    assert risk_bucket(60.0) == 1
    assert risk_bucket(60.01) == 2
    assert risk_bucket(100.0) == 2
    s = np.array([10.0, 45.0, 75.0])
    np.testing.assert_array_equal(risk_class_from_scores(s), [0, 1, 2])
