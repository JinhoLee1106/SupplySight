# services/census/ingest_shrimp.py
from __future__ import annotations
import argparse
import os
from pathlib import Path
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import pandas as pd
from dotenv import load_dotenv

from services.census.client import HSImportsQuery, fetch_hs_imports, CensusError
from services.product_config import ProductConfig, get_product_config

load_dotenv()
ROOT = Path(__file__).resolve().parents[2]   # repo root
PROCESSED_DIR = ROOT / "database" / "processed"
RAW_DIR = ROOT / "database" / "raw" / "shrimp_imports"
OUT_CSV = PROCESSED_DIR / "shrimp_imports.csv"

FIELDS = ["I_COMMODITY", "I_COMMODITY_SDESC", "GEN_VAL_MO", "VES_WGT_MO", "CNT_WGT_MO", "AIR_WGT_MO"]

def month_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _parse_time_from_month(s: str) -> datetime:
    """First day of month for ``YYYY-MM``."""
    s = s.strip()
    d = pd.to_datetime(s, format="%Y-%m")
    return datetime(d.year, d.month, 1)

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

def product_paths(config: ProductConfig) -> tuple[Path, Path]:
    if config.name == "shrimp":
        return RAW_DIR, OUT_CSV
    raw_dir = ROOT / "database" / "raw" / f"{config.name}_imports"
    out_csv = PROCESSED_DIR / f"{config.name}_imports.csv"
    return raw_dir, out_csv


def fetch_for_hs_codes(
    api_key: str,
    time_from: str,
    time_to: str,
    hs_codes: tuple[str, ...],
) -> pd.DataFrame:
    """
    Fetch imports for all target HS codes.

    For each 6-digit HS code, try the 10-digit version first (e.g. 0306160000),
    then fall back to the 6-digit code (e.g. 030616). Concatenate all results.
    """
    all_frames: list[pd.DataFrame] = []
    last_exc: Exception | None = None

    for hs6 in hs_codes:
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
        raise CensusError(f"Failed to fetch imports for HS codes {list(hs_codes)}. Last error: {last_exc}")

    return pd.concat(all_frames, ignore_index=True)


def fetch_with_fallback(api_key: str, time_from: str, time_to: str) -> pd.DataFrame:
    """Backward-compatible shrimp fetch helper used by older tests."""
    return fetch_for_hs_codes(api_key, time_from, time_to, get_product_config("shrimp").hs_codes)

def run(
    product: str = "shrimp",
    months_back: int | None = None,
    time_from_arg: str | None = None,
    time_to_arg: str | None = None,
) -> dict:
    config = get_product_config(product)
    api_key = os.getenv("CENSUS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Set CENSUS_API_KEY in your environment (or GitHub Actions secret).")

    if months_back is None:
        months_back = int(os.getenv("SHRIMP_MONTHS_BACK", "96"))

    # CLI wins, then env SHRIMP_TIME_FROM; otherwise rolling months_back
    tf = (time_from_arg or "").strip() or os.getenv("SHRIMP_TIME_FROM", "").strip() or None

    raw_dir, out_csv = product_paths(config)
    ensure_dirs(raw_dir, PROCESSED_DIR)

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    if tf:
        start_dt = _parse_time_from_month(tf)
        mode = "explicit"
    else:
        start_dt = today - relativedelta(months=months_back)
        mode = "rolling"
    time_from_str = month_str(start_dt)

    # Latest month inclusive: CLI --time-to, env SHRIMP_TIME_TO, or current month
    tt_end = (time_to_arg or "").strip() or os.getenv("SHRIMP_TIME_TO", "").strip() or None
    if tt_end:
        end_dt = _parse_time_from_month(tt_end)
    else:
        end_dt = today
    if end_dt < start_dt:
        raise ValueError("End month (--time-to / SHRIMP_TIME_TO) must be on or after start month.")
    time_to_str = month_str(end_dt)

    if config.name == "shrimp":
        df_raw = fetch_with_fallback(api_key, time_from_str, time_to_str)
    else:
        df_raw = fetch_for_hs_codes(api_key, time_from_str, time_to_str, config.hs_codes)
    df_clean_new = clean(df_raw)

    # Save raw snapshot
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_path = raw_dir / f"{config.name}_imports_snapshot_{stamp}.csv"
    df_raw.to_csv(raw_path, index=False)

    # Merge into existing processed dataset
    df_existing = read_csv_if_exists(out_csv)
    if len(df_existing) > 0:
        df_existing["MONTH"] = df_existing["MONTH"].astype(str)

    df_merged = pd.concat([df_existing, df_clean_new], ignore_index=True)
    # Ensure we keep a single row per (commodity, month) across all HS codes.
    df_merged = df_merged.sort_values(["I_COMMODITY", "MONTH"]).drop_duplicates(
        subset=["I_COMMODITY", "MONTH"], keep="last"
    )
    df_merged = df_merged.reset_index(drop=True)

    atomic_write_csv(df_merged, out_csv)

    return {
        "product": config.name,
        "pulled_range": f"{time_from_str} to {time_to_str}",
        "time_from_mode": mode,
        "rows_new_window": int(len(df_clean_new)),
        "rows_total": int(len(df_merged)),
        "raw_snapshot": str(raw_path),
        "output_csv": str(out_csv),
        "min_time": df_merged["MONTH"].min() if len(df_merged) else None,
        "max_time": df_merged["MONTH"].max() if len(df_merged) else None,
    }

def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch Census seafood HS imports and merge into a product-specific processed CSV."
    )
    p.add_argument(
        "--product",
        type=str,
        default="shrimp",
        help="Product to ingest. Supported: shrimp, salmon, tuna, whitefish.",
    )
    p.add_argument(
        "--time-from",
        type=str,
        default=None,
        metavar="YYYY-MM",
        help="Earliest month to fetch (e.g. 2013-01). Overrides SHRIMP_MONTHS_BACK rolling window.",
    )
    p.add_argument(
        "--months-back",
        type=int,
        default=None,
        help="Rolling window in months (default: env SHRIMP_MONTHS_BACK or 96). Ignored if --time-from or SHRIMP_TIME_FROM is set.",
    )
    p.add_argument(
        "--time-to",
        type=str,
        default=None,
        metavar="YYYY-MM",
        help="Latest month to fetch (e.g. 2026-12). Default: current month. Env: SHRIMP_TIME_TO.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _cli()
    summary = run(
        product=args.product,
        months_back=args.months_back,
        time_from_arg=args.time_from,
        time_to_arg=args.time_to,
    )
    print(summary)
