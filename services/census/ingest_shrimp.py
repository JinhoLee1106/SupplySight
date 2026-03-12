# services/census/ingest_shrimp.py
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import pandas as pd
from dotenv import load_dotenv

from services.census.client import HSImportsQuery, fetch_hs_imports, CensusError

load_dotenv()
ROOT = Path(__file__).resolve().parents[2]   # repo root
RAW_DIR = ROOT / "database" / "raw" / "shrimp_imports"
PROCESSED_DIR = ROOT / "database" / "processed"
OUT_CSV = PROCESSED_DIR / "shrimp_imports.csv"

FIELDS = ["I_COMMODITY", "I_COMMODITY_SDESC", "GEN_VAL_MO", "VES_WGT_MO", "CNT_WGT_MO", "AIR_WGT_MO"]

# 6-digit HS codes for shrimp that we care about.
# 030616 = certain frozen shrimp/prawns
# 030617 = other frozen shrimp/prawns
TARGET_HS_CODES = ["030616", "030617"]

def month_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m")

def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

def atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(path)

def clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MONTH"] = out["MONTH"].astype(str)
    out["I_COMMODITY"] = out["I_COMMODITY"].astype(str)
    # Convert numeric columns
    for col in ["GEN_VAL_MO", "VES_WGT_MO", "CNT_WGT_MO", "AIR_WGT_MO"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["GEN_VAL_MO"], how="any")
    # Keep one row per (commodity, month) pair; allow multiple HS codes overall.
    out = out.sort_values(["I_COMMODITY", "MONTH"]).drop_duplicates(
        subset=["I_COMMODITY", "MONTH"], keep="last"
    )
    out = out.reset_index(drop=True)
    return out

def fetch_for_hs_codes(api_key: str, time_from: str, time_to: str) -> pd.DataFrame:
    """
    Fetch imports for all target HS codes.

    For each 6-digit HS code, try the 10-digit version first (e.g. 0306160000),
    then fall back to the 6-digit code (e.g. 030616). Concatenate all results.
    """
    all_frames: list[pd.DataFrame] = []
    last_exc: Exception | None = None

    for hs6 in TARGET_HS_CODES:
        for hs in (f"{hs6}0000", hs6):
            q = HSImportsQuery(hs_code=hs, time_from=time_from, time_to=time_to, fields=FIELDS)
            try:
                df = fetch_hs_imports(q, api_key=api_key)
                if len(df) > 0:
                    all_frames.append(df)
                    break  # move to next hs6 code
            except Exception as e:
                last_exc = e
                continue

    if not all_frames:
        raise CensusError(f"Failed to fetch shrimp imports for HS codes {TARGET_HS_CODES}. Last error: {last_exc}")

    return pd.concat(all_frames, ignore_index=True)

def run(months_back: int | None = None) -> dict:
    api_key = os.getenv("CENSUS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Set CENSUS_API_KEY in your environment (or GitHub Actions secret).")

    # allow override via environment variable; default to 96 months (~8 years)
    if months_back is None:
        months_back = int(os.getenv("SHRIMP_MONTHS_BACK", "96"))

    ensure_dirs(RAW_DIR, PROCESSED_DIR)

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    start_dt = today - relativedelta(months=months_back)
    time_from = month_str(start_dt)
    time_to = month_str(today)

    df_raw = fetch_for_hs_codes(api_key, time_from, time_to)
    df_clean_new = clean(df_raw)

    # Save raw snapshot
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"shrimp_imports_snapshot_{stamp}.csv"
    df_raw.to_csv(raw_path, index=False)

    # Merge into existing processed dataset
    df_existing = read_csv_if_exists(OUT_CSV)
    if len(df_existing) > 0:
        df_existing["MONTH"] = df_existing["MONTH"].astype(str)

    df_merged = pd.concat([df_existing, df_clean_new], ignore_index=True)
    # Ensure we keep a single row per (commodity, month) across all HS codes.
    df_merged = df_merged.sort_values(["I_COMMODITY", "MONTH"]).drop_duplicates(
        subset=["I_COMMODITY", "MONTH"], keep="last"
    )
    df_merged = df_merged.reset_index(drop=True)

    atomic_write_csv(df_merged, OUT_CSV)

    return {
        "pulled_range": f"{time_from} to {time_to}",
        "rows_new_window": int(len(df_clean_new)),
        "rows_total": int(len(df_merged)),
        "raw_snapshot": str(raw_path),
        "output_csv": str(OUT_CSV),
        "min_time": df_merged["MONTH"].min() if len(df_merged) else None,
        "max_time": df_merged["MONTH"].max() if len(df_merged) else None,
    }

if __name__ == "__main__":
    summary = run()
    print(summary)