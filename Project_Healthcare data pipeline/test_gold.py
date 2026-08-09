"""Unit tests for Gold Layer Aggregations."""
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from src.gold import process_gold_layer


@pytest.fixture
def mock_silver_csv(tmp_path):
    """Creates a mock Silver CSV file containing both current and expired historical records."""
    silver_file = tmp_path / "patient_records_silver.csv"
    data = [
        # Active encounter 1 (Hospital A, Billing 10000)
        {
            "Name": "John Smith", "Date of Admission": "2024-01-10", "Hospital": "Hospital A", "Doctor": "Dr. Miller",
            "Billing Amount": 10000.00, "Age": 40, "Medical Condition": "Diabetes", "Admission Type": "Emergency",
            "Insurance Provider": "Medicare", "Test Results": "Normal", "is_current": True, "encounter_key": "k1"
        },
        # Expired encounter 1 (Historical version — should be excluded from Gold state analytics)
        {
            "Name": "John Smith", "Date of Admission": "2024-01-10", "Hospital": "Hospital A", "Doctor": "Dr. Miller",
            "Billing Amount": 8000.00, "Age": 40, "Medical Condition": "Diabetes", "Admission Type": "Emergency",
            "Insurance Provider": "Medicare", "Test Results": "Normal", "is_current": False, "encounter_key": "k1"
        },
        # Active encounter 2 (Hospital A, Billing 20000)
        {
            "Name": "Mary Johnson", "Date of Admission": "2024-02-15", "Hospital": "Hospital A", "Doctor": "Dr. Miller",
            "Billing Amount": 20000.00, "Age": 60, "Medical Condition": "Asthma", "Admission Type": "Elective",
            "Insurance Provider": "Aetna", "Test Results": "Abnormal", "is_current": True, "encounter_key": "k2"
        },
        # Active encounter 3 (Hospital B, Billing 15000)
        {
            "Name": "Bob Lee", "Date of Admission": "2024-03-01", "Hospital": "Hospital B", "Doctor": "Dr. Davis",
            "Billing Amount": 15000.00, "Age": 25, "Medical Condition": "Diabetes", "Admission Type": "Urgent",
            "Insurance Provider": "Cigna", "Test Results": "Inconclusive", "is_current": True, "encounter_key": "k3"
        }
    ]
    pd.DataFrame(data).to_csv(silver_file, index=False)
    return silver_file


def test_gold_aggregations(mock_silver_csv, tmp_path):
    gold_dir = tmp_path / "gold"
    json_path = tmp_path / "gold_data.json"

    tables = process_gold_layer(
        silver_path=mock_silver_csv,
        gold_dir=gold_dir,
        json_path=json_path
    )

    # Check that 8 tables were generated
    assert len(tables) == 8

    # Check Hospital Ranking (Hospital A: 2 patients, Total Billing = 30000.00)
    ranking = tables["hospital_ranking"]
    assert len(ranking) == 2
    top_hospital = ranking.iloc[0]
    assert top_hospital["Hospital"] == "Hospital A"
    assert top_hospital["patient_count"] == 2
    assert top_hospital["total_billing"] == 30000.00

    # Check Condition Analysis (Diabetes: 2 patients, Total Billing = 25000.00)
    condition = tables["contribution_by_medical_condition"]
    diabetes_row = condition[condition["Medical Condition"] == "Diabetes"].iloc[0]
    assert diabetes_row["patient_count"] == 2
    assert diabetes_row["total_billing"] == 25000.00

    # Check JSON snapshot creation
    assert json_path.exists()
