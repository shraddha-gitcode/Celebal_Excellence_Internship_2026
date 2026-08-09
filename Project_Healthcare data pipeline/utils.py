"""Utility functions for hashing, deterministic keys, and Data Quality validations & reports."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from src.config import DQ_REPORT_PATH, REPORTS_DIR
from src.logger import get_logger

logger = get_logger("data_quality")


def compute_encounter_key(df: pd.DataFrame, business_cols: List[str]) -> pd.Series:
    """Vectorized calculation of deterministic encounter business key (MD5 hash)."""
    raw_series = df[business_cols[0]].astype(str)
    for col in business_cols[1:]:
        raw_series = raw_series + "|" + df[col].astype(str)
    return raw_series.apply(lambda x: hashlib.md5(x.encode("utf-8")).hexdigest())


def compute_hash_diff(df: pd.DataFrame, tracked_cols: List[str]) -> pd.Series:
    """Vectorized calculation of hash diff for tracked attribute changes (MD5 hash)."""
    raw_series = df[tracked_cols[0]].astype(str)
    for col in tracked_cols[1:]:
        raw_series = raw_series + "|" + df[col].astype(str)
    return raw_series.apply(lambda x: hashlib.md5(x.encode("utf-8")).hexdigest())


# ---------------------------------------------------------------------------
# Data Quality Tracker & Report Generator
# ---------------------------------------------------------------------------

class DataQualityMetrics:
    """Dataclass to capture measurable pipeline metrics for audit reporting."""
    def __init__(self):
        self.source_row_count: int = 0
        self.bronze_row_count: int = 0
        self.duplicate_count: int = 0
        self.null_count: int = 0
        self.invalid_date_count: int = 0
        self.invalid_billing_count: int = 0
        self.silver_total_count: int = 0
        self.silver_current_count: int = 0
        self.silver_historical_count: int = 0
        self.scd2_validation: str = "PENDING"
        self.gold_tables_count: int = 0
        self.gold_validation: str = "PENDING"
        self.overall_status: str = "PASS"

    def to_dict(self) -> Dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_row_count": self.source_row_count,
            "bronze_row_count": self.bronze_row_count,
            "duplicate_count": self.duplicate_count,
            "null_count": self.null_count,
            "invalid_date_count": self.invalid_date_count,
            "invalid_billing_count": self.invalid_billing_count,
            "silver_total_count": self.silver_total_count,
            "silver_current_count": self.silver_current_count,
            "silver_historical_count": self.silver_historical_count,
            "scd2_validation": self.scd2_validation,
            "gold_tables_count": self.gold_tables_count,
            "gold_validation": self.gold_validation,
            "overall_status": self.overall_status
        }


def save_data_quality_report(metrics: DataQualityMetrics, report_path: Optional[Path] = None) -> Path:
    """Exports structured data quality report to JSON."""
    out_path = report_path or DQ_REPORT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = metrics.to_dict()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Data Quality Report successfully written to: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Data Quality Assertions
# ---------------------------------------------------------------------------

def validate_bronze_data(df: pd.DataFrame) -> None:
    """Validate Bronze layer DataFrame integrity."""
    if df is None or df.empty:
        raise ValueError("Data Quality Error: Bronze DataFrame is empty or None.")

    required_meta = ["_ingestion_timestamp", "_source_file", "_bronze_row_id"]
    missing_meta = [col for col in required_meta if col not in df.columns]
    if missing_meta:
        raise ValueError(f"Data Quality Error: Missing Bronze metadata columns: {missing_meta}")


def validate_silver_data(df: pd.DataFrame, critical_cols: List[str]) -> bool:
    """Validate Silver layer DataFrame integrity and SCD2 constraints."""
    if df is None or df.empty:
        raise ValueError("Data Quality Error: Silver DataFrame is empty or None.")

    for col in critical_cols:
        if col not in df.columns:
            raise ValueError(f"Data Quality Error: Critical column '{col}' missing from Silver table.")
        null_count = df[col].isna().sum()
        if null_count > 0:
            raise ValueError(f"Data Quality Error: Silver table contains {null_count} nulls in critical column '{col}'.")

    scd_fields = ["encounter_key", "effective_start_date", "is_current", "hash_diff", "_scd_surrogate_key"]
    for field in scd_fields:
        if field not in df.columns:
            raise ValueError(f"Data Quality Error: Missing SCD2 field '{field}' in Silver table.")

    # Check SCD2 Current Record Uniqueness constraint: exactly 1 current record per encounter_key
    current_records = df[df["is_current"] == True]
    duplicate_current_keys = current_records[current_records.duplicated(subset=["encounter_key"], keep=False)]
    if not duplicate_current_keys.empty:
        n_dupes = len(duplicate_current_keys["encounter_key"].unique())
        raise ValueError(f"Data Quality Error: SCD2 constraint violation! Found {n_dupes} encounter_keys with multiple active records.")

    if "_dq_negative_billing" in df.columns:
        invalid_negative = (df["Billing Amount"] < 0).sum()
        if invalid_negative > 0:
            raise ValueError(f"Data Quality Error: Found {invalid_negative} uncorrected negative billing amounts in Silver table.")

    return True


def validate_gold_tables(tables: Dict[str, pd.DataFrame]) -> bool:
    """Validate Gold aggregated tables before output."""
    if not tables:
        raise ValueError("Data Quality Error: No Gold tables were generated.")

    for name, table in tables.items():
        if table is None or table.empty:
            raise ValueError(f"Data Quality Error: Gold table '{name}' is empty.")

    return True
