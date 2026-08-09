"""BRONZE LAYER — Raw Data Ingestion

Preserves raw patient records as received from source systems without mutating
business values. Adds standard metadata columns for lineage and auditability.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import pandas as pd

from src.config import BRONZE_DATA_PATH, SOURCE_DATA_PATH
from src.logger import get_logger
from src.utils import validate_bronze_data

logger = get_logger("bronze")


def ingest_to_bronze(
    source_path: Optional[Path] = None,
    output_path: Optional[Path] = None
) -> pd.DataFrame:
    """Reads raw CSV dataset as strings, appends metadata, and saves to Bronze directory."""
    src_file = source_path or SOURCE_DATA_PATH
    out_file = output_path or BRONZE_DATA_PATH

    logger.info("=" * 70)
    logger.info(f"BRONZE LAYER — Ingesting Raw Dataset from: {src_file.name}")
    logger.info("=" * 70)

    if not src_file.exists():
        logger.error(f"Source file not found: {src_file}")
        raise FileNotFoundError(f"Source file not found at: {src_file}")

    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Read raw data as string to prevent silent type mutation
    df = pd.read_csv(src_file, dtype=str)
    logger.info(f"Discovered {len(df):,} raw source records across {len(df.columns)} columns.")

    # Append ingestion metadata
    df["_ingestion_timestamp"] = datetime.now(timezone.utc).isoformat()
    df["_source_file"] = src_file.name
    df["_bronze_row_id"] = range(1, len(df) + 1)

    # Data Quality Validation
    validate_bronze_data(df)

    # Save Bronze dataset
    df.to_csv(out_file, index=False)

    logger.info(f"Bronze Ingestion Complete: {len(df):,} rows saved to {out_file.name}")
    return df


if __name__ == "__main__":
    ingest_to_bronze()
