# tests/test_supply_risk_labels.py

from __future__ import annotations

import pandas as pd

from services.supply_risk_labels import (
    attach_labels_to_days,
    monthly_raw_stress,
    monthly_scaled_labels,
)


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
    y_m = monthly_scaled_labels(months, train_days, p_ref=90.0)
    y_same = attach_labels_to_days(
        pd.Series(pd.to_datetime(["2024-01-15"])), y_m, label_month="same"
    )
    y_next = attach_labels_to_days(
        pd.Series(pd.to_datetime(["2024-01-15"])), y_m, label_month="next"
    )
    assert y_same.notna().all() and y_next.notna().all()
    assert float(y_same.iloc[0]) != float(y_next.iloc[0])
