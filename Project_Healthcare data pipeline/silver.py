"""SILVER LAYER — Data Cleaning, Standardization & SCD Type 2 MERGE

Transforms raw Bronze data into a clean, deduplicated, standardized Silver dataset.
Tracks historical record updates using SCD Type 2 logic (emulating Delta Lake MERGE semantics).
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd

from src.config import BRONZE_DATA_PATH, CRITICAL_FIELDS, SILVER_DATA_PATH, TRACKED_COLS, BUSINESS_KEY_COLS
from src.logger import get_logger
from src.utils import compute_encounter_key, compute_hash_diff, validate_silver_data, DataQualityMetrics

logger = get_logger("silver")


def clean_silver_data(df: pd.DataFrame, metrics: Optional[DataQualityMetrics] = None) -> pd.DataFrame:
    """Cleans, standardizes, and validates incoming data for the Silver layer."""
    df = df.copy()
    stats = {"duplicates": 0, "nulls": 0, "negative_billing": 0, "invalid_dates": 0}

    # Standardize casing & trim whitespace
    for col in ["Name", "Doctor", "Hospital"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    for col in ["Gender", "Blood Type", "Medical Condition", "Insurance Provider",
                "Admission Type", "Medication", "Test Results"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    # Dates standardization (ISO YYYY-MM-DD)
    if "Date of Admission" in df.columns:
        parsed_adm = pd.to_datetime(df["Date of Admission"], errors="coerce")
        stats["invalid_dates"] += int(parsed_adm.isna().sum())
        df["Date of Admission"] = parsed_adm.dt.strftime("%Y-%m-%d")

    if "Discharge Date" in df.columns:
        parsed_dis = pd.to_datetime(df["Discharge Date"], errors="coerce")
        stats["invalid_dates"] += int(parsed_dis.isna().sum())
        df["Discharge Date"] = parsed_dis.dt.strftime("%Y-%m-%d")

    # Numeric conversions
    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce").astype("Int64")
    if "Room Number" in df.columns:
        df["Room Number"] = pd.to_numeric(df["Room Number"], errors="coerce").astype("Int64")
    if "Billing Amount" in df.columns:
        df["Billing Amount"] = pd.to_numeric(df["Billing Amount"], errors="coerce").round(2)

    # Flag negative billing
    if "Billing Amount" in df.columns:
        neg_mask = df["Billing Amount"] < 0
        stats["negative_billing"] = int(neg_mask.sum())
        df["_dq_negative_billing"] = neg_mask
        df.loc[neg_mask, "Billing Amount"] = df.loc[neg_mask, "Billing Amount"].abs()

    # Remove exact duplicate business rows
    business_cols = [c for c in df.columns if not c.startswith("_")]
    before_dups = len(df)
    df = df.drop_duplicates(subset=business_cols).reset_index(drop=True)
    stats["duplicates"] = before_dups - len(df)
    logger.info(f"Silver Cleaning: Removed {stats['duplicates']:,} exact duplicate rows.")

    # Remove rows with nulls in critical fields
    before_nulls = len(df)
    df = df.dropna(subset=CRITICAL_FIELDS).reset_index(drop=True)
    stats["nulls"] = before_nulls - len(df)
    if stats["nulls"] > 0:
        logger.info(f"Silver Cleaning: Removed {stats['nulls']:,} rows with missing critical fields.")

    if metrics:
        metrics.duplicate_count += stats["duplicates"]
        metrics.null_count += stats["nulls"]
        metrics.invalid_billing_count += stats["negative_billing"]
        metrics.invalid_date_count += stats["invalid_dates"]

    return df


def scd2_merge(
    existing: Optional[pd.DataFrame],
    incoming: pd.DataFrame,
    load_date: str
) -> pd.DataFrame:
    """Applies Slowly Changing Dimension (SCD) Type 2 MERGE semantics."""
    if incoming is None or incoming.empty:
        return existing if existing is not None else pd.DataFrame()

    inc = incoming.copy()
    inc["encounter_key"] = compute_encounter_key(inc, BUSINESS_KEY_COLS)
    inc["hash_diff"] = compute_hash_diff(inc, TRACKED_COLS)

    inc = inc.drop_duplicates(subset=["encounter_key"], keep="last").reset_index(drop=True)

    if existing is None or existing.empty:
        inc["effective_start_date"] = load_date
        inc["effective_end_date"] = None
        inc["is_current"] = True
        inc["_scd_surrogate_key"] = range(1, len(inc) + 1)
        logger.info(f"SCD2 Initial Load ({load_date}): Inserted {len(inc):,} initial active records.")
        return inc

    ext = existing.copy()
    max_sk = int(ext["_scd_surrogate_key"].max()) if "_scd_surrogate_key" in ext.columns else 0

    current_mask = ext["is_current"] == True
    current_df = ext[current_mask].copy()

    merged = inc.merge(
        current_df[["encounter_key", "hash_diff"]],
        on="encounter_key",
        how="left",
        suffixes=("", "_current")
    )

    new_mask = merged["hash_diff_current"].isna()
    changed_mask = merged["hash_diff_current"].notna() & (merged["hash_diff"] != merged["hash_diff_current"])
    unchanged_mask = merged["hash_diff_current"].notna() & (merged["hash_diff"] == merged["hash_diff_current"])

    new_records = merged[new_mask].drop(columns=["hash_diff_current"]).copy()
    changed_records = merged[changed_mask].drop(columns=["hash_diff_current"]).copy()

    # Expire old records in existing dataset
    changed_keys = set(changed_records["encounter_key"])
    expire_mask = (ext["is_current"] == True) & (ext["encounter_key"].isin(changed_keys))

    ext.loc[expire_mask, "is_current"] = False
    ext.loc[expire_mask, "effective_end_date"] = load_date

    # Insert new & updated records
    to_insert = pd.concat([new_records, changed_records], ignore_index=True)
    if not to_insert.empty:
        to_insert["effective_start_date"] = load_date
        to_insert["effective_end_date"] = None
        to_insert["is_current"] = True
        to_insert["_scd_surrogate_key"] = range(max_sk + 1, max_sk + 1 + len(to_insert))

    n_inserted = len(new_records)
    n_changed = len(changed_records)
    n_expired = int(expire_mask.sum())
    n_unchanged = int(unchanged_mask.sum())

    logger.info(f"SCD2 MERGE Execution ({load_date}):")
    logger.info(f"  Brand-new encounters inserted : {n_inserted:,}")
    logger.info(f"  Changed encounters (new ver) : {n_changed:,}")
    logger.info(f"  Expired historical versions   : {n_expired:,}")
    logger.info(f"  Unchanged encounters          : {n_unchanged:,}")

    result = pd.concat([ext, to_insert], ignore_index=True)
    return result


def simulate_incremental_updates(df: pd.DataFrame, sample_size: int = 250, seed: int = 42) -> pd.DataFrame:
    """Simulates real-world incremental attribute updates to test SCD2 logic."""
    rng = np.random.default_rng(seed)
    sample_idx = rng.choice(df.index, size=min(sample_size, len(df)), replace=False)
    updated = df.loc[sample_idx].copy()
    updated["Billing Amount"] = (updated["Billing Amount"] * rng.uniform(0.95, 1.08, size=len(updated))).round(2)
    updated["Test Results"] = rng.choice(["Normal", "Abnormal", "Inconclusive"], size=len(updated))
    return updated


def process_silver_layer(
    bronze_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    metrics: Optional[DataQualityMetrics] = None,
    incremental_path: Optional[Path] = None
) -> pd.DataFrame:
    """Executes full Silver layer pipeline with cleaning and SCD2 MERGE."""
    b_path = bronze_path or BRONZE_DATA_PATH
    s_path = output_path or SILVER_DATA_PATH

    logger.info("=" * 70)
    logger.info("SILVER LAYER — Data Cleaning, Standardization & SCD Type 2 MERGE")
    logger.info("=" * 70)

    if not b_path.exists():
        logger.error(f"Bronze dataset missing: {b_path}")
        raise FileNotFoundError(f"Bronze file not found at: {b_path}")

    s_path.parent.mkdir(parents=True, exist_ok=True)

    bronze_df = pd.read_csv(b_path, dtype=str)
    cleaned_df = clean_silver_data(bronze_df, metrics)

    # Initial Load (Day 1: 90%)
    split_idx = int(len(cleaned_df) * 0.9)
    day1_batch = cleaned_df.iloc[:split_idx].reset_index(drop=True)
    day2_new = cleaned_df.iloc[split_idx:].reset_index(drop=True)
    day2_updates = simulate_incremental_updates(day1_batch, sample_size=250)
    day2_batch = pd.concat([day2_new, day2_updates], ignore_index=True)

    # Run Day 1 Initial Merge
    silver_df = scd2_merge(None, day1_batch, load_date="2024-06-01")

    # Run Day 2 Incremental Simulation Merge
    silver_df = scd2_merge(silver_df, day2_batch, load_date="2024-06-02")

    # Process external incremental batch if provided
    if incremental_path and incremental_path.exists():
        logger.info(f"Processing External Incremental Batch: {incremental_path.name}")
        inc_raw = pd.read_csv(incremental_path, dtype=str)
        inc_clean = clean_silver_data(inc_raw, metrics)
        silver_df = scd2_merge(silver_df, inc_clean, load_date=datetime.now().strftime("%Y-%m-%d"))

    # Validate Silver data quality & SCD2 constraints
    if validate_silver_data(silver_df, CRITICAL_FIELDS):
        if metrics:
            metrics.scd2_validation = "PASS"

    # Save Silver dataset
    silver_df.to_csv(s_path, index=False)

    n_current = int((silver_df["is_current"] == True).sum())
    n_history = int((silver_df["is_current"] == False).sum())

    if metrics:
        metrics.silver_total_count = len(silver_df)
        metrics.silver_current_count = n_current
        metrics.silver_historical_count = n_history

    logger.info("Silver Layer Execution Summary:")
    logger.info(f"  Total Silver Records (Current + Expired) : {len(silver_df):,}")
    logger.info(f"  Active Current Records (is_current=True)  : {n_current:,}")
    logger.info(f"  Expired Historical Records (SCD2 history): {n_history:,}")
    logger.info(f"  Saved to                                 : {s_path.name}")

    return silver_df


if __name__ == "__main__":
    process_silver_layer()
