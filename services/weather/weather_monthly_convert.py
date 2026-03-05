import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "database" / "processed" / "weather_hourly.csv"
OUTPUT_FILE =  ROOT / "database" / "processed" / "weather_monthly_summary.csv"

# Load
df = pd.read_csv(INPUT_FILE)

# Parse time 
df["time"] = pd.to_datetime(df["time"], errors="coerce")
df = df.dropna(subset=["time"])

# Ensure numeric (coerce bad strings to NaN)
num_cols = [
    "sea_surface_temperature",
    "wave_height",
    "ocean_current_velocity",
    "sea_level_height_msl",
]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Month key as YYYY-MM
df["MONTH"] = df["time"].dt.to_period("M").astype(str)

# Aggregate to monthly
monthly = df.groupby("MONTH", as_index=False).agg(
    SST_MEAN=("sea_surface_temperature", "mean"),
    SST_STD=("sea_surface_temperature", "std"),
    WVH_MEAN=("wave_height", "mean"),
    WVH_STD=("wave_height", "std"),
    WVH_MAX=("wave_height", "max"),
    OCV_MEAN=("ocean_current_velocity", "mean"),
    OCV_STD=("ocean_current_velocity", "std"),
    SLHMSL_MEAN=("sea_level_height_msl", "mean"),
    SLHMSL_STD=("sea_level_height_msl", "std"),
    N_OBS=("time", "count"),
)

# Optional: round to match your desired display precision
# SST .1f, WVH .2f, OCV .1f, SLHMSL .2f
monthly["SST_MEAN"] = monthly["SST_MEAN"].round(1)
monthly["SST_STD"] = monthly["SST_STD"].round(1)
monthly["WVH_MEAN"] = monthly["WVH_MEAN"].round(2)
monthly["WVH_STD"] = monthly["WVH_STD"].round(2)
monthly["WVH_MAX"] = monthly["WVH_MAX"].round(2)
monthly["OCV_MEAN"] = monthly["OCV_MEAN"].round(1)
monthly["OCV_STD"] = monthly["OCV_STD"].round(1)
monthly["SLHMSL_MEAN"] = monthly["SLHMSL_MEAN"].round(2)
monthly["SLHMSL_STD"] = monthly["SLHMSL_STD"].round(2)

# Save monthly summary
monthly.to_csv(OUTPUT_FILE, index=False)
print("Saved:", OUTPUT_FILE)