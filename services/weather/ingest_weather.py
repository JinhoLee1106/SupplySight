# services/weather/ingest_weather.py

from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "database" / "processed"
OUT_CSV = PROCESSED_DIR / "weather_hourly.csv"

API_URL = "https://marine-api.open-meteo.com/v1/marine"

PARAMS = {
    "latitude": 17.68,
    "longitude": 83.21,
    "hourly": "sea_surface_temperature,wave_height,ocean_current_velocity,sea_level_height_msl",
    "models": "best_match",
    "start_date": "2022-01-01",
    "end_date": "2025-01-01"
}


def fetch_weather():
    r = requests.get(API_URL, params=PARAMS, timeout=60)
    r.raise_for_status()
    data = r.json()

    hourly = data["hourly"]

    df = pd.DataFrame({
        "time": hourly["time"],
        "sea_surface_temperature": hourly["sea_surface_temperature"],
        "wave_height": hourly["wave_height"],
        "ocean_current_velocity": hourly["ocean_current_velocity"],
        "sea_level_height_msl": hourly["sea_level_height_msl"]
    })

    return df


def main():

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_weather()

    df.to_csv(OUT_CSV, index=False)

    print(f"Saved {len(df)} rows → {OUT_CSV}")


if __name__ == "__main__":
    main()