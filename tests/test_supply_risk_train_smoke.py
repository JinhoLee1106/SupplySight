# tests/test_supply_risk_train_smoke.py

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer


def test_imputer_rf_roundtrip(tmp_path) -> None:
    rng = np.random.default_rng(0)
    X = pd.DataFrame(
        {
            "m__a": rng.normal(size=40),
            "m__b": rng.normal(size=40),
            "d__x": rng.normal(size=40),
            "d__y": rng.normal(size=40),
        }
    )
    X.loc[0, "d__x"] = np.nan
    y = (X["m__a"] * 0.5 + X["d__x"].fillna(0) * 0.3).clip(0, 100)
    imputer = SimpleImputer(strategy="median")
    Xi = imputer.fit_transform(X)
    rf = RandomForestRegressor(n_estimators=10, random_state=0, max_depth=4)
    rf.fit(Xi[:30], y.iloc[:30])
    pred = rf.predict(imputer.transform(X.iloc[30:]))
    assert pred.shape == (10,)
    bundle = {"imputer": imputer, "feature_names": list(X.columns), "model": rf, "two_stage": False}
    path = tmp_path / "b.joblib"
    joblib.dump(bundle, path)
    b2 = joblib.load(path)
    assert b2["model"].predict(b2["imputer"].transform(X.iloc[[31]])).shape == (1,)
