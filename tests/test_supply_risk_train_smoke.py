# tests/test_supply_risk_train_smoke.py

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from services.risk_model_infer import predict_risk_class_batch_from_bundle, raw_predict_batch
from services.supply_risk_training.supply_risk_train import (
    _fit_monthly_classifier,
    _fit_monthly_linear,
    _monthly_risk_class_truth,
)
from services.supply_risk_training.supply_risk_labels import risk_bucket


def test_monthly_risk_class_truth_mode_not_mean_bucket() -> None:
    """Classifier truth = mode of daily 0–2 bands; can differ from bucket(mean(y))."""
    frame = pd.DataFrame(
        {
            "label_ym": ["2024-01", "2024-01"],
            "y": [25.0, 75.0],
        }
    )
    mask = pd.Series([True, True])
    s = _monthly_risk_class_truth(frame, mask)
    assert int(s["2024-01"]) == 0
    assert risk_bucket(float(frame["y"].mean())) == 1


def test_fit_monthly_linear() -> None:
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 4))
    y = X.sum(axis=1) + rng.normal(scale=0.1, size=30)
    est, meta = _fit_monthly_linear(X, y)
    assert meta["monthly_regressor"] == "linear_regression"
    assert est.predict(X).shape == (30,)


def test_formula_bundle_joblib_roundtrip(tmp_path) -> None:
    rng = np.random.default_rng(0)
    m_names = ["m__a", "m__b"]
    d_names = ["d__oil_price", "d__sentiment_score"]
    n = 40
    Xm = rng.normal(size=(n, 2))
    Xd = rng.normal(size=(n, 2))
    Xd[0, 0] = np.nan
    y_m = Xm.sum(axis=1)
    im_m = SimpleImputer(strategy="median")
    im_m.fit(Xm)
    lr_m = Pipeline(
        [("scaler", StandardScaler()), ("lr", LinearRegression())]
    )
    lr_m.fit(im_m.transform(Xm), y_m)

    formula_meta = {
        "kind": "oil_sentiment_train_minmax",
        "oil_lo": 0.0,
        "oil_hi": 100.0,
        "oil_med": 50.0,
        "sent_lo": -1.0,
        "sent_hi": 1.0,
        "sent_med": 0.0,
        "w_oil": 0.125,
        "w_sent": 0.125,
        "adjustment_scale": 20.0,
    }
    bundle = {
        "architecture": "monthly_plus_formula_adjustment",
        "feature_names": m_names + d_names,
        "m_feature_names": m_names,
        "d_feature_names": d_names,
        "imputer_month": im_m,
        "rf_month": lr_m,
        "formula_meta": formula_meta,
        "d_oil_ix": 0,
        "d_sent_ix": 1,
        "delta_clip": 10.0,
        "monthly_regressor": "linear_regression",
    }
    path = tmp_path / "b.joblib"
    joblib.dump(bundle, path)
    b2 = joblib.load(path)
    Xrow = np.hstack([Xm[[31]], Xd[[31]]])
    assert raw_predict_batch(b2, Xrow).shape == (1,)


def test_fit_monthly_classifier_skips_single_class() -> None:
    X = np.ones((5, 2))
    y = np.zeros(5, dtype=int)
    est, meta = _fit_monthly_classifier(X, y)
    assert est is None
    assert meta["monthly_classifier_kind"] == "skipped_few_classes"


def test_fit_monthly_classifier_random_forest() -> None:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 3))
    y = (X[:, 0] > 0).astype(int) + (X[:, 1] > 0).astype(int)
    est, meta = _fit_monthly_classifier(X, y)
    assert est is not None
    assert meta["monthly_classifier_kind"] == "random_forest"


def test_predict_risk_class_batch_from_bundle() -> None:
    rng = np.random.default_rng(3)
    m_names = ["m__a", "m__b"]
    d_names = ["d__oil_price", "d__sentiment_score"]
    n = 24
    Xm = rng.normal(size=(n, 2))
    y_c = (Xm[:, 0] + Xm[:, 1] > 0).astype(int)
    im_m = SimpleImputer(strategy="median")
    im_m.fit(Xm)
    clf, meta = _fit_monthly_classifier(im_m.transform(Xm), y_c)
    assert meta["monthly_classifier_kind"] == "random_forest"
    assert clf is not None
    Xd = rng.normal(size=(n, 2))
    bundle = {
        "m_feature_names": m_names,
        "d_feature_names": d_names,
        "imputer_month": im_m,
        "monthly_classifier": clf,
    }
    X = np.hstack([Xm, Xd])
    got = predict_risk_class_batch_from_bundle(bundle, X)
    assert got is not None
    assert got.shape == (n,)
    no_clf = {**bundle, "monthly_classifier": None}
    assert predict_risk_class_batch_from_bundle(no_clf, X) is None
