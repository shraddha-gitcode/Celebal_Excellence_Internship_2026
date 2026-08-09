"""Unit tests for Bronze Layer Ingestion."""
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from src.bronze import ingest_to_bronze


@pytest.fixture
def sample_csv(tmp_path):
    """Creates a temporary sample source CSV file for testing."""
    csv_file = tmp_path / "sample_source.csv"
    content = (
        "Name,Age,Gender,Blood Type,Medical Condition,Date of Admission,Doctor,Hospital,Insurance Provider,Billing Amount,Room Number,Admission Type,Discharge Date,Medication,Test Results\n"
        "John Doe,45,Male,O+,Diabetes,2024-01-15,Dr. Smith,General Hospital,Medicare,15000.50,101,Emergency,2024-01-20,Metformin,Normal\n"
        "Jane Miller,32,Female,A-,Asthma,2024-02-10,Dr. Jones,City Clinic,Aetna,-2500.00,202,Elective,2024-02-12,Albuterol,Abnormal\n"
    )
    csv_file.write_text(content, encoding="utf-8")
    return csv_file


def test_bronze_ingestion(sample_csv, tmp_path):
    out_file = tmp_path / "patient_records_bronze.csv"

    bronze_df = ingest_to_bronze(source_path=sample_csv, output_path=out_file)

    # Check row count
    assert len(bronze_df) == 2

    # Check ingestion metadata columns exist
    assert "_ingestion_timestamp" in bronze_df.columns
    assert "_source_file" in bronze_df.columns
    assert "_bronze_row_id" in bronze_df.columns

    # Check raw value preservation (negative billing should be preserved in Bronze)
    assert bronze_df.loc[1, "Billing Amount"] == "-2500.00"

    # Check output file creation
    assert out_file.exists()
