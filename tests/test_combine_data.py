"""
tests/test_combine_data.py

Test the data combination script.
"""
import pandas as pd
import pytest
from pathlib import Path
from services.combine_data import (
    load_shrimp_imports,
    load_price_index,
    load_shrimp_features,
    load_weather_features,
    combine_all_data
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "database" / "processed"


def test_load_functions_handle_missing_files():
    """Test that load functions gracefully handle missing files."""
    # These should return empty DataFrames without crashing
    df = load_shrimp_imports()
    assert isinstance(df, pd.DataFrame)


def test_combine_with_sample_data(tmp_path, monkeypatch):
    """Test combining data with sample CSV files."""
    
    # Create temporary processed directory
    test_processed = tmp_path / "database" / "processed"
    test_processed.mkdir(parents=True)
    
    # Create sample shrimp imports
    imports_df = pd.DataFrame({
        "I_COMMODITY": ["030617", "030617"],
        "I_COMMODITY_SDESC": ["Frozen shrimp", "Frozen shrimp"],
        "GEN_VAL_MO": [1000, 2000],
        "VES_WGT_MO": [100, 200],
        "CNT_WGT_MO": [50, 100],
        "AIR_WGT_MO": [10, 20],
        "MONTH": ["2024-01", "2024-02"]
    })
    imports_df.to_csv(test_processed / "shrimp_imports.csv", index=False)
    
    # Create sample price index
    price_dir = test_processed / "price_data"
    price_dir.mkdir(parents=True)
    price_df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01"],
        "commodity": ["Shrimp", "Shrimp"],
        "value": [100.5, 101.2],
        "source": ["FAO", "FAO"],
        "source_file": ["file1.csv", "file2.csv"],
        "ingested_at": ["2024-01-01", "2024-02-01"]
    })
    price_df.to_csv(price_dir / "fao_shrimp_price_index.csv", index=False)
    
    # Create sample features
    features_df = pd.DataFrame({
        "I_COMMODITY": ["030617", "030617"],
        "MONTH": ["2024-01", "2024-02"],
        "total_weight_mo": [110, 220],
        "air_share": [0.09, 0.09],
        "container_ratio": [0.5, 0.5],
        "unit_value_per_kg": [9.09, 9.09],
        "weight_mom_pct": [0.0, 1.0],
        "weight_yoy_pct": [0.0, 0.0],
        "unit_value_mom_pct": [0.0, 0.0],
        "air_share_mom_delta": [0.0, 0.0],
        "weight_roll3_avg": [110, 165],
        "weight_roll6_avg": [110, 165],
        "weight_roll3_std": [0, 55],
        "weight_roll6_std": [0, 55],
        "weight_zscore_6": [0, 1]
    })
    features_df.to_csv(test_processed / "shrimp_features.csv", index=False)
    
    # Create sample weather
    weather_df = pd.DataFrame({
        "MONTH": ["2024-01", "2024-02"],
        "sst_avg": [25.5, 26.0],
        "wave_height_max": [2.5, 3.0],
        "ocean_current_avg": [0.5, 0.6],
        "sea_level_avg": [0.1, 0.2]
    })
    weather_df.to_csv(test_processed / "weather_features.csv", index=False)
    
    # Patch the PROCESSED_DIR constant
    import services.combine_data as combine_module
    monkeypatch.setattr(combine_module, "PROCESSED_DIR", test_processed)
    monkeypatch.setattr(combine_module, "SHRIMP_IMPORTS", test_processed / "shrimp_imports.csv")
    monkeypatch.setattr(combine_module, "PRICE_INDEX", price_dir / "fao_shrimp_price_index.csv")
    monkeypatch.setattr(combine_module, "SHRIMP_FEATURES", test_processed / "shrimp_features.csv")
    monkeypatch.setattr(combine_module, "WEATHER_FEATURES", test_processed / "weather_features.csv")
    
    # Run combination
    combined = combine_all_data()
    
    # Assertions
    assert len(combined) == 2
    assert "MONTH" in combined.columns
    assert "GEN_VAL_MO" in combined.columns
    assert "price_index_value" in combined.columns
    assert "total_weight_mo" in combined.columns
    assert "sst_avg" in combined.columns
    
    # Check that data was properly merged
    assert combined.loc[0, "GEN_VAL_MO"] == 1000
    assert combined.loc[0, "price_index_value"] == 100.5
    assert combined.loc[0, "total_weight_mo"] == 110
    assert combined.loc[0, "sst_avg"] == 25.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
