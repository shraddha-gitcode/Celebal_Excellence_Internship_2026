"""Master Pipeline Orchestrator — Production-Ready Local Execution

Runs the end-to-end Medallion Healthcare Data Pipeline:
    Source Data -> Bronze -> Silver (SCD Type 2) -> Gold -> Data Quality Report & Dashboard Sync
"""
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bronze import ingest_to_bronze
from src.config import INCREMENTAL_DATA_DIR, SOURCE_DATA_PATH
from src.gold import process_gold_layer
from src.logger import get_logger
from src.silver import process_silver_layer
from src.utils import DataQualityMetrics, save_data_quality_report

logger = get_logger("pipeline")


def run_pipeline():
    """Executes the complete Medallion pipeline end-to-end with structured logging & DQ audit reporting."""
    start_time = time.time()
    metrics = DataQualityMetrics()

    logger.info("#" * 70)
    logger.info("# HEALTHCARE DATA PIPELINE — PRODUCTION-READY MEDALLION EXECUTION")
    logger.info("#" * 70)

    try:
        # Discover inputs
        if SOURCE_DATA_PATH.exists():
            import pandas as pd
            raw_len = len(pd.read_csv(SOURCE_DATA_PATH, dtype=str))
            metrics.source_row_count = raw_len
            logger.info(f"Input Discovery: Found primary source dataset '{SOURCE_DATA_PATH.name}' ({raw_len:,} records).")
        else:
            logger.error(f"Input Discovery Error: Source dataset not found at {SOURCE_DATA_PATH}")

        # Check incremental batch
        inc_batch = None
        if INCREMENTAL_DATA_DIR.exists():
            inc_files = list(INCREMENTAL_DATA_DIR.glob("*.csv"))
            if inc_files:
                inc_batch = inc_files[0]
                logger.info(f"Input Discovery: Found incremental batch dataset '{inc_batch.name}' in {INCREMENTAL_DATA_DIR.name}/")

        # 1. Bronze Layer Ingestion
        bronze_df = ingest_to_bronze(source_path=SOURCE_DATA_PATH)
        metrics.bronze_row_count = len(bronze_df)

        # 2. Silver Layer Cleaning & SCD Type 2 MERGE
        silver_df = process_silver_layer(metrics=metrics, incremental_path=inc_batch)

        # 3. Gold Layer Aggregations & Dashboard JSON Sync
        gold_tables = process_gold_layer(metrics=metrics)

        # Final Data Quality Audit Report Generation
        metrics.overall_status = "PASS"
        report_file = save_data_quality_report(metrics)

        elapsed = time.time() - start_time
        logger.info(f"SUCCESS: Healthcare Data Pipeline completed in {elapsed:.2f} seconds.")
        logger.info(f"  Data Quality Audit Status : {metrics.overall_status}")
        logger.info(f"  Data Quality Report Saved : {report_file.name}")
        logger.info(f"  Pipeline Log File Saved   : logs/pipeline.log\n")

    except Exception as e:
        metrics.overall_status = "FAIL"
        save_data_quality_report(metrics)
        logger.error(f"FAILURE: Pipeline execution failed with error: {e}", exc_info=True)
        raise e


if __name__ == "__main__":
    run_pipeline()
