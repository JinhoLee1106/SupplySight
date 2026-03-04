# services/weather/feature_engineering_weather.py

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = ROOT / "database" / "processed" / "weather_hourly.csv"
OUTPUT = ROOT / "database" / "processed" / "weather_features.csv"


def build_features():

    df = pd.read_csv(INPUT)

    df["time"] = pd.to_datetime(df["time"])
    
    # month column
    df["MONTH"] = df["time"].dt.to_period("M")

    monthly = df.groupby("MONTH").agg({
        "sea_surface_temperature": "mean",
        "wave_height": "max",
        "ocean_current_velocity": "mean",
        "sea_level_height_msl": "mean"
    }).reset_index()

    monthly["MONTH"] = monthly["MONTH"].astype(str)

    monthly = monthly.rename(columns={
        "sea_surface_temperature": "sst_avg",
        "wave_height": "wave_height_max",
        "ocean_current_velocity": "ocean_current_avg",
        "sea_level_height_msl": "sea_level_avg"
    })

    return monthly


def main():

    features = build_features()

    features.to_csv(OUTPUT, index=False)

    print(f"Saved features → {OUTPUT}")
    print(features.head())
    print(features["MONTH"].unique()[:10])


if __name__ == "__main__":
    main()