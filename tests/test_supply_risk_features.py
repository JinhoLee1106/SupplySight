# tests/test_supply_risk_features.py

from __future__ import annotations

import pandas as pd

from services.supply_risk_training.supply_risk_features import (
    MONTHLY_MODEL_FEATURES,
    build_monthly_feature_table,
    build_training_frame,
    describe_monthly_validation_failure,
    mask_valid_monthly_rows,
    month_anchor,
    resolve_monthly_model_feature_names,
    train_validation_masks_by_month,
)


def test_month_anchor_same_month() -> None:
    d = pd.Series(pd.to_datetime(["2024-03-15", "2024-01-01"]))
    m = month_anchor(d, "same_month")
    assert m.iloc[0] == pd.Timestamp("2024-03-01")
    assert m.iloc[1] == pd.Timestamp("2024-01-01")


def test_month_anchor_prev_month() -> None:
    d = pd.Series(pd.to_datetime(["2024-03-15"]))
    m = month_anchor(d, "prev_month")
    assert m.iloc[0] == pd.Timestamp("2024-02-01")


def test_build_training_frame_prefixes_and_join() -> None:
    daily = pd.DataFrame(
        {
            "date": ["2024-03-10", "2024-03-11"],
            "oil_price": [80.0, 81.0],
            "sentiment_score": [0.0, -0.5],
        }
    )
    monthly = pd.DataFrame(
        {
            "date": ["2024-03-01"],
            "monthly_import": [1e6],
            "monthly_import_zscore_6": [-0.5],
            "price_index_value": [92.0],
            "avg_air_share": [0.1],
            "avg_container_ratio": [0.9],
            "monthly_import_mom_pct": [0.0],
            "monthly_import_yoy_pct": [0.0],
            "monthly_import_roll3_avg": [1e6],
            "monthly_import_roll6_avg": [1e6],
            "monthly_import_roll3_std": [1.0],
            "monthly_import_roll6_std": [1.0],
            "avg_unit_value_per_kg": [10.0],
        }
    )
    frame, names = build_training_frame(daily, monthly, monthly_lag="same_month")
    assert "d__oil_price" in names and "m__monthly_import" in names
    assert names == sorted(n for n in names if n.startswith("m__")) + sorted(
        n for n in names if n.startswith("d__")
    )
    assert len(frame) == 2
    assert frame["m__monthly_import"].iloc[0] == 1e6


def test_mask_valid_monthly_rows() -> None:
    daily = pd.DataFrame(
        {
            "date": ["2024-03-10", "2024-04-10"],
            "oil_price": [80.0, 81.0],
        }
    )
    monthly = pd.DataFrame(
        {
            "date": ["2024-03-01"],
            "monthly_import": [1e6],
            "monthly_import_zscore_6": [-0.5],
            "price_index_value": [92.0],
            "avg_air_share": [0.1],
            "avg_container_ratio": [0.9],
            "monthly_import_mom_pct": [0.0],
            "monthly_import_yoy_pct": [0.0],
            "monthly_import_roll3_avg": [1e6],
            "monthly_import_roll6_avg": [1e6],
            "monthly_import_roll3_std": [1.0],
            "monthly_import_roll6_std": [1.0],
            "avg_unit_value_per_kg": [10.0],
        }
    )
    frame, _ = build_training_frame(daily, monthly, monthly_lag="same_month")
    m = mask_valid_monthly_rows(frame)
    assert bool(m.iloc[0]) is True
    assert bool(m.iloc[1]) is False


def test_describe_monthly_validation_failure_lists_missing() -> None:
    daily = pd.DataFrame({"date": ["2024-04-10"], "oil_price": [80.0]})
    monthly = pd.DataFrame(
        {
            "date": ["2024-03-01"],
            "monthly_import": [1e6],
            "monthly_import_zscore_6": [-0.5],
            "price_index_value": [92.0],
            "avg_air_share": [0.1],
            "avg_container_ratio": [0.9],
            "monthly_import_mom_pct": [0.0],
            "monthly_import_yoy_pct": [0.0],
            "monthly_import_roll3_avg": [1e6],
            "monthly_import_roll6_avg": [1e6],
            "monthly_import_roll3_std": [1.0],
            "monthly_import_roll6_std": [1.0],
            "avg_unit_value_per_kg": [10.0],
        }
    )
    frame, _ = build_training_frame(daily, monthly, monthly_lag="same_month")
    msg = describe_monthly_validation_failure(frame.iloc[0], "same_month")
    assert "2024-04" in msg or "2024-04-01" in msg
    assert "m__monthly_import_zscore_6" in msg


def test_build_monthly_feature_table() -> None:
    monthly = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01"],
            "monthly_import": [1.0, 2.0],
            "price_index_value": [90.0, 91.0],
        }
    )
    tbl, m_names = build_monthly_feature_table(monthly)
    assert list(tbl["ym"]) == ["2024-01", "2024-02"]
    assert "m__monthly_import" in m_names and "m__price_index_value" in m_names


def test_resolve_monthly_model_feature_names_default() -> None:
    names = list(MONTHLY_MODEL_FEATURES) + ["m__avg_air_share", "d__oil_price"]
    got = resolve_monthly_model_feature_names(names)
    assert got == list(MONTHLY_MODEL_FEATURES)
    assert "m__avg_air_share" not in got


def test_resolve_monthly_model_feature_names_override() -> None:
    names = ["m__a", "m__b", "d__x"]
    got = resolve_monthly_model_feature_names(names, raw_override="a,b")
    assert got == ["m__a", "m__b"]


def test_train_validation_masks() -> None:
    d = pd.Series(
        pd.to_datetime(
            ["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05", "2024-05-05"]
        )
    )
    tr, va = train_validation_masks_by_month(d, holdout_months=2)
    assert tr.sum() == 3 and va.sum() == 2
