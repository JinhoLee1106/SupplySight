#!/usr/bin/env python3
"""
services/combine_data.py

Combine all processed data sources into a single unified CSV file.

Data sources:
1. shrimp_imports.csv - US Census import data (monthly)
2. fao_shrimp_price_index.csv - FAO price index (monthly)
3. shrimp_features.csv - Engineered features from imports (monthly)
4. weather_features.csv - Ocean weather data aggregated monthly

All data is merged on MONTH/date column.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "database" / "processed"

# Input files
SHRIMP_IMPORTS = PROCESSED_DIR / "shrimp_imports.csv"
SHRIMP_FEATURES = PROCESSED_DIR / "shrimp_features.csv"
PRICE_INDEX = PROCESSED_DIR / "fao_shrimp_price_index.csv"
WEATHER_FEATURES = PROCESSED_DIR / "weather_features.csv"

# Output file
COMBINED_OUTPUT = PROCESSED_DIR / "combined_data.csv"


def load_shrimp_imports() -> pd.DataFrame:
    """Load shrimp imports data."""
    if not SHRIMP_IMPORTS.exists():
        print(f"Warning: {SHRIMP_IMPORTS} not found, skipping.")
        return pd.DataFrame()

    df = pd.read_csv(SHRIMP_IMPORTS)
    if "MONTH" in df.columns:
        df["MONTH"] = pd.to_datetime(df["MONTH"], format="%Y-%m")
    return df


def load_price_index() -> pd.DataFrame:
    """Load FAO price index data."""
    if not PRICE_INDEX.exists():
        print(f"Warning: {PRICE_INDEX} not found, skipping.")
        return pd.DataFrame()
    
    df = pd.read_csv(PRICE_INDEX)
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"date": "MONTH"})
    
    # Prefix price columns to avoid conflicts
    rename_cols = {
        "value": "price_index_value",
        "commodity": "price_commodity",
        "source": "price_source",
        "source_file": "price_source_file",
        "ingested_at": "price_ingested_at"
    }
    df = df.rename(columns=rename_cols)
    return df


def load_shrimp_features() -> pd.DataFrame:
    """Load engineered features from census data."""
    if not SHRIMP_FEATURES.exists():
        print(f"Warning: {SHRIMP_FEATURES} not found, skipping.")
        return pd.DataFrame()
    
    df = pd.read_csv(SHRIMP_FEATURES)
    df["MONTH"] = pd.to_datetime(df["MONTH"], format="%Y-%m")
    
    # Select only the engineered features (exclude raw columns already in imports)
    feature_cols = [
        "I_COMMODITY",
        "MONTH",
        "total_weight_mo",
        "air_share",
        "container_ratio",
        "unit_value_per_kg",
        "weight_mom_pct",
        "weight_yoy_pct",
        "unit_value_mom_pct",
        "air_share_mom_delta",
        "weight_roll3_avg",
        "weight_roll6_avg",
        "weight_roll3_std",
        "weight_roll6_std",
        "weight_zscore_6"
    ]
    # Keep only columns that exist
    feature_cols = [c for c in feature_cols if c in df.columns]
    df = df[feature_cols]
    return df


def load_weather_features() -> pd.DataFrame:
    """Load weather features data."""
    if not WEATHER_FEATURES.exists():
        print(f"Warning: {WEATHER_FEATURES} not found, skipping.")
        return pd.DataFrame()
    
    df = pd.read_csv(WEATHER_FEATURES)
    df["MONTH"] = pd.to_datetime(df["MONTH"], format="%Y-%m")
    return df


def combine_all_data() -> pd.DataFrame:
    """Combine all data sources into a single DataFrame."""    
    # Load all data
    imports_df = load_shrimp_imports()
    price_df = load_price_index()
    features_df = load_shrimp_features()
    weather_df = load_weather_features()
    
    # Start with price index as the base
    if price_df.empty:
        print("\n Error: fao_shrimp_price_index.csv is required as the base dataset.")
        sys.exit(1)
    
    combined = price_df.copy()

    # Merge raw imports first so legacy downstream users keep access to the
    # monthly Census value/weight columns.
    if not imports_df.empty:
        combined = combined.merge(
            imports_df,
            on="MONTH",
            how="left"
        )

    # Merge engineered features (one-to-one on MONTH and commodity)
    if not features_df.empty:
        combined = combined.merge(
            features_df,
            on="MONTH",
            how="left"
        )    
    # Merge weather features (many-to-one: multiple commodities per month)
    if not weather_df.empty:
        combined = combined.merge(
            weather_df,
            on="MONTH",
            how="left"
        )
    
    # Convert MONTH back to string format for output
    combined["MONTH"] = combined["MONTH"].dt.strftime("%Y-%m")
    
    return combined


def main():
    """Main execution function."""
    
    print("="*60)
    print("Combining All Processed Data Sources")
    print("="*60)
    
    # Combine all data
    combined_df = combine_all_data()
    
    # Save to output
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(COMBINED_OUTPUT, index=False)
    
    print(f"\n{'='*60}")
    print(f"SUCCESS: Combined data saved")
    print(f"{'='*60}")
    print(f"Output: {COMBINED_OUTPUT}")
    print(f"Total rows: {len(combined_df):,}")
    print(f"Total columns: {len(combined_df.columns)}")
    print(f"\nColumns ({len(combined_df.columns)}):")
    for i, col in enumerate(combined_df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    # Show date range
    if not combined_df.empty:
        print(f"\nDate range: {combined_df['MONTH'].min()} to {combined_df['MONTH'].max()}")

    # Show data completeness
    print(f"\nData Completeness:")
    missing_pct = (combined_df.isnull().sum() / len(combined_df) * 100).round(1)
    for col, pct in missing_pct[missing_pct > 0].items():
        print(f"  {col}: {pct}% missing")


if __name__ == "__main__":
    main()
