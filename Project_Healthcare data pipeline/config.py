"""Configuration management for the Healthcare Data Pipeline.

Provides environment-agnostic, project-relative paths using pathlib.Path.
"""
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Pipeline Directory Paths
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_DATA_PATH = DATA_DIR / "source_data.csv"
INCREMENTAL_DATA_DIR = DATA_DIR / "incremental"

BRONZE_DIR = PROJECT_ROOT / "bronze"
BRONZE_DATA_PATH = BRONZE_DIR / "patient_records_bronze.csv"

SILVER_DIR = PROJECT_ROOT / "silver"
SILVER_DATA_PATH = SILVER_DIR / "patient_records_silver.csv"

GOLD_DIR = PROJECT_ROOT / "gold"

DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
DASHBOARD_JSON_PATH = DASHBOARD_DIR / "gold_data.json"

REPORTS_DIR = PROJECT_ROOT / "reports"
DQ_REPORT_PATH = REPORTS_DIR / "data_quality_report.json"

LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE_PATH = LOGS_DIR / "pipeline.log"

# Data Schema & Attributes
BUSINESS_KEY_COLS = ["Name", "Date of Admission", "Hospital", "Doctor"]

TRACKED_COLS = [
    "Billing Amount",
    "Room Number",
    "Admission Type",
    "Discharge Date",
    "Medication",
    "Test Results"
]

CRITICAL_FIELDS = ["Name", "Date of Admission", "Hospital", "Billing Amount"]
