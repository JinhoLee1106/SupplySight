from pathlib import Path

import pandas as pd

from services import combined_monthly_data as cmd


def test_build_monthly_and_price(tmp_path: Path) -> None:
    """
    Smoke test for the monthly pipeline:
    - writes tiny shrimp_features.csv and fao_shrimp_price_index.csv
    - overrides paths in combined_monthly_data
    - asserts basic shape and expected columns
    """
    # Prepare tiny shrimp_features.csv
    shrimp_path = tmp_path / "shrimp_features.csv"
    shrimp_df = pd.DataFrame(
        {
            "I_COMMODITY": ["30616", "30617"],
            "MONTH": ["2024-01", "2024-01"],
            "total_weight_mo": [100.0, 200.0],
            "unit_value_per_kg": [8.0, 9.0],
            "air_share": [0.1, 0.2],
            "container_ratio": [0.9, 0.8],
            "weight_mom_pct": [0.05, 0.10],
            "weight_yoy_pct": [0.10, 0.20],
            "weight_roll3_avg": [100.0, 200.0],
            "weight_roll6_avg": [100.0, 200.0],
            "weight_roll3_std": [0.0, 0.0],
            "weight_roll6_std": [0.0, 0.0],
            "weight_zscore_6": [0.0, 0.0],
        }
    )
    shrimp_df.to_csv(shrimp_path, index=False)

    # Prepare tiny fao_shrimp_price_index.csv
    price_path = tmp_path / "fao_shrimp_price_index.csv"
    price_df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "commodity": ["shrimp"],
            "value": [120.0],
            "source": ["test"],
            "source_file": ["test.csv"],
            "ingested_at": ["2024-01-01T00:00:00"],
        }
    )
    price_df.to_csv(price_path, index=False)

    # Monkey-patch module paths to point to tmp files
    cmd.SHRIMP_FEATURES = shrimp_path
    cmd.PRICE_INDEX = price_path

    db_frame = cmd.build_months_shrimp_dataframe()

    assert len(db_frame) == 1
    assert "date" in db_frame.columns and "MONTH" not in db_frame.columns
    assert list(db_frame.columns) == cmd.MONTHS_SHRIMP_COLUMNS
    assert db_frame["date"].iloc[0] == pd.Timestamp("2024-01-01")
    assert set(cmd.MONTHS_SHRIMP_COLUMNS) == set(db_frame.columns)

    legacy = cmd.monthly_training_csv_from_db_frame(db_frame)
    assert "MONTH" in legacy.columns and "date" not in legacy.columns
    assert legacy["MONTH"].iloc[0] == "2024-01"

    legacy_path = tmp_path / "monthly_training_data.csv"
    legacy.to_csv(legacy_path, index=False)
    roundtrip = cmd.load_months_shrimp_from_legacy_csv(legacy_path)
    pd.testing.assert_frame_equal(roundtrip.reset_index(drop=True), db_frame.reset_index(drop=True))
