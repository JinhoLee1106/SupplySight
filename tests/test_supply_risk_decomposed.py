# tests/test_supply_risk_decomposed.py

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

from services.risk_model_infer import (
    decomposed_components_from_bundle,
    raw_predict_batch,
)
from services.supply_risk_training.supply_risk_labels import (
    daily_adjustment_oil_sentiment_batch,
    label_month_key_series,
    y_mean_by_label_month,
)


def test_label_month_key_series_same_and_next() -> None:
    d = pd.Series(pd.to_datetime(["2024-01-15", "2024-02-20"]))
    s = label_month_key_series(d, label_month="same")
    assert list(s) == ["2024-01", "2024-02"]
    n = label_month_key_series(d, label_month="next")
    assert list(n) == ["2024-02", "2024-03"]


def test_y_mean_by_label_month() -> None:
    idx = pd.RangeIndex(4)
    ym = pd.Series(["2024-01", "2024-01", "2024-02", "2024-02"], index=idx)
    y = pd.Series([10.0, 20.0, 30.0, 50.0], index=idx)
    tr = pd.Series([True, True, True, False], index=idx)
    out = y_mean_by_label_month(ym, y, tr)
    assert abs(float(out["2024-01"]) - 15.0) < 1e-9
    assert abs(float(out["2024-02"]) - 30.0) < 1e-9


def test_formula_components_and_raw_predict_match() -> None:
    rng = np.random.default_rng(2)
    nm, nd = 1, 2
    m_names = ["m__a"]
    d_names = ["d__oil_price", "d__sentiment_score"]
    n = 10
    Xm = rng.random((n, nm))
    Xd = rng.random((n, nd))
    y_m = Xm.ravel() * 3
    rf_m = RandomForestRegressor(n_estimators=8, random_state=0, max_depth=3)
    im_m = SimpleImputer(strategy="median")
    im_m.fit(Xm)
    rf_m.fit(im_m.transform(Xm), y_m)

    formula_meta = {
        "kind": "oil_sentiment_train_minmax",
        "oil_lo": 0.0,
        "oil_hi": 1.0,
        "oil_med": 0.5,
        "sent_lo": 0.0,
        "sent_hi": 1.0,
        "sent_med": 0.5,
        "w_oil": 0.125,
        "w_sent": 0.125,
        "adjustment_scale": 20.0,
    }
    bundle = {
        "architecture": "monthly_plus_formula_adjustment",
        "m_feature_names": m_names,
        "d_feature_names": d_names,
        "feature_names": m_names + d_names,
        "imputer_month": im_m,
        "rf_month": rf_m,
        "formula_meta": formula_meta,
        "d_oil_ix": 0,
        "d_sent_ix": 1,
        "delta_clip": 50.0,
    }
    X = np.hstack([Xm, Xd])
    mr, da, raw = decomposed_components_from_bundle(bundle, X)
    assert mr.shape == (n,) and da.shape == (n,) and raw.shape == (n,)
    batch = raw_predict_batch(bundle, X)
    np.testing.assert_allclose(batch, raw, rtol=1e-6)


def test_legacy_rf_delta_components_and_raw_predict_match() -> None:
    rng = np.random.default_rng(0)
    nm, nd = 2, 2
    m_names = ["m__a", "m__b"]
    d_names = ["d__x", "d__y"]
    n = 30
    Xm = rng.random((n, nm))
    Xd = rng.random((n, nd))
    y_m = Xm.sum(axis=1)
    rf_m = RandomForestRegressor(n_estimators=10, random_state=0, max_depth=4)
    rf_m.fit(Xm, y_m)
    monthly_pred = rf_m.predict(Xm)
    delta_t = rng.normal(scale=0.5, size=n)
    rf_d = RandomForestRegressor(n_estimators=10, random_state=1, max_depth=4)
    rf_d.fit(np.column_stack([Xd, monthly_pred]), delta_t)

    im_m = SimpleImputer(strategy="median")
    im_d = SimpleImputer(strategy="median")
    im_m.fit(Xm)
    im_d.fit(Xd)

    dc = 10.0
    bundle = {
        "architecture": "monthly_plus_daily_delta",
        "m_feature_names": m_names,
        "d_feature_names": d_names,
        "feature_names": m_names + d_names,
        "imputer_month": im_m,
        "imputer_delta": im_d,
        "rf_month": rf_m,
        "rf_delta": rf_d,
        "delta_clip": dc,
    }

    X = rng.random((5, nm + nd))
    mr, da, raw = decomposed_components_from_bundle(bundle, X)
    assert mr.shape == (5,) and da.shape == (5,) and raw.shape == (5,)
    assert np.all(np.abs(da) <= dc + 1e-6)
    batch = raw_predict_batch(bundle, X)
    np.testing.assert_allclose(batch, raw, rtol=1e-6)


def test_daily_adjustment_neutral_when_midpoint() -> None:
    meta = {
        "oil_lo": 0.0,
        "oil_hi": 100.0,
        "oil_med": 50.0,
        "sent_lo": 0.0,
        "sent_hi": 100.0,
        "sent_med": 50.0,
        "w_oil": 0.125,
        "w_sent": 0.125,
        "adjustment_scale": 20.0,
    }
    d = np.array([[50.0, 50.0]], dtype=float)
    out = daily_adjustment_oil_sentiment_batch(d, meta, 0, 1, delta_clip=100.0)
    np.testing.assert_allclose(out, [0.0], atol=1e-6)
