import types
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

    monthly = cmd.build_monthly_from_shrimp()
    price = cmd.load_price_index()

    # Basic expectations
    assert len(monthly) == 1
    assert len(price) == 1

    combined = monthly.merge(price, on="MONTH", how="left")
    expected_cols = {
        "MONTH",
        "monthly_import",
        "avg_unit_value_per_kg",
        "avg_air_share",
        "avg_container_ratio",
        "monthly_import_mom_pct",
        "monthly_import_yoy_pct",
        "monthly_import_roll3_avg",
        "monthly_import_roll6_avg",
        "monthly_import_roll3_std",
        "monthly_import_roll6_std",
        "monthly_import_zscore_6",
        "price_index_value",
    }
    assert expected_cols.issubset(set(combined.columns))

