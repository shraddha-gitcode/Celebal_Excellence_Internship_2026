"""Unit tests for Data Quality Report generation and Structured Logging."""
import json
import tempfile
from pathlib import Path
import pytest

from src.config import DQ_REPORT_PATH, LOG_FILE_PATH
from src.logger import get_logger
from src.utils import DataQualityMetrics, save_data_quality_report


def test_data_quality_report_export(tmp_path):
    metrics = DataQualityMetrics()
    metrics.source_row_count = 55500
    metrics.bronze_row_count = 55500
    metrics.duplicate_count = 534
    metrics.null_count = 0
    metrics.invalid_date_count = 0
    metrics.invalid_billing_count = 96
    metrics.silver_total_count = 50250
    metrics.silver_current_count = 50000
    metrics.silver_historical_count = 250
    metrics.scd2_validation = "PASS"
    metrics.gold_tables_count = 8
    metrics.gold_validation = "PASS"
    metrics.overall_status = "PASS"

    report_path = tmp_path / "data_quality_report.json"
    save_data_quality_report(metrics, report_path=report_path)

    assert report_path.exists()

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["source_row_count"] == 55500
    assert data["duplicate_count"] == 534
    assert data["scd2_validation"] == "PASS"
    assert data["overall_status"] == "PASS"


def test_pipeline_logging(tmp_path):
    logger = get_logger("test_logger")
    logger.info("Test log event: pipeline started successfully.")

    assert LOG_FILE_PATH.exists()
    content = LOG_FILE_PATH.read_text(encoding="utf-8")
    assert "Test log event: pipeline started successfully." in content
