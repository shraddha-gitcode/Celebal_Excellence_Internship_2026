"""Unit tests for Silver Layer Cleaning, Standardization, and SCD Type 2 MERGE."""
import pandas as pd
import pytest

from src.silver import clean_silver_data, scd2_merge


@pytest.fixture
def raw_dirty_df():
    """Provides a sample dirty DataFrame for testing Silver cleaning."""
    return pd.DataFrame([
        {
            "Name": "  john doe ",
            "Age": "45",
            "Gender": "male",
            "Blood Type": "o+",
            "Medical Condition": "diabetes",
            "Date of Admission": "2024/01/15",
            "Doctor": "dr. smith",
            "Hospital": "general hospital",
            "Insurance Provider": "medicare",
            "Billing Amount": "-15000.50",
            "Room Number": "101",
            "Admission Type": "emergency",
            "Discharge Date": "2024-01-20",
            "Medication": "metformin",
            "Test Results": "normal"
        },
        {
            # Exact duplicate row
            "Name": "  john doe ",
            "Age": "45",
            "Gender": "male",
            "Blood Type": "o+",
            "Medical Condition": "diabetes",
            "Date of Admission": "2024/01/15",
            "Doctor": "dr. smith",
            "Hospital": "general hospital",
            "Insurance Provider": "medicare",
            "Billing Amount": "-15000.50",
            "Room Number": "101",
            "Admission Type": "emergency",
            "Discharge Date": "2024-01-20",
            "Medication": "metformin",
            "Test Results": "normal"
        },
        {
            # Null critical field (Name missing)
            "Name": None,
            "Age": "30",
            "Gender": "female",
            "Blood Type": "a+",
            "Medical Condition": "asthma",
            "Date of Admission": "2024-02-01",
            "Doctor": "dr. jones",
            "Hospital": "city clinic",
            "Insurance Provider": "aetna",
            "Billing Amount": "5000.00",
            "Room Number": "202",
            "Admission Type": "urgent",
            "Discharge Date": "2024-02-05",
            "Medication": "albuterol",
            "Test Results": "abnormal"
        }
    ])


def test_clean_silver_data(raw_dirty_df):
    cleaned = clean_silver_data(raw_dirty_df)

    # 1. Row count (1 exact duplicate removed, 1 null-name removed -> 1 row left)
    assert len(cleaned) == 1

    row = cleaned.iloc[0]
    # 2. Text standardization
    assert row["Name"] == "John Doe"
    assert row["Doctor"] == "Dr. Smith"
    assert row["Hospital"] == "General Hospital"
    assert row["Medical Condition"] == "Diabetes"

    # 3. Date standardization (ISO format YYYY-MM-DD)
    assert row["Date of Admission"] == "2024-01-15"

    # 4. Negative billing correction & audit flag
    assert row["_dq_negative_billing"] == True
    assert row["Billing Amount"] == 15000.50


def test_scd2_merge_new_record():
    incoming = pd.DataFrame([{
        "Name": "Alice Brown",
        "Date of Admission": "2024-03-01",
        "Hospital": "St Jude",
        "Doctor": "Dr. House",
        "Billing Amount": 12000.00,
        "Room Number": 305,
        "Admission Type": "Elective",
        "Discharge Date": "2024-03-05",
        "Medication": "Aspirin",
        "Test Results": "Normal"
    }])

    silver = scd2_merge(None, incoming, load_date="2024-06-01")

    assert len(silver) == 1
    assert silver.iloc[0]["is_current"] == True
    assert silver.iloc[0]["effective_start_date"] == "2024-06-01"
    assert pd.isna(silver.iloc[0]["effective_end_date"]) or silver.iloc[0]["effective_end_date"] is None
    assert silver.iloc[0]["_scd_surrogate_key"] == 1


def test_scd2_merge_unchanged_record():
    incoming = pd.DataFrame([{
        "Name": "Alice Brown",
        "Date of Admission": "2024-03-01",
        "Hospital": "St Jude",
        "Doctor": "Dr. House",
        "Billing Amount": 12000.00,
        "Room Number": 305,
        "Admission Type": "Elective",
        "Discharge Date": "2024-03-05",
        "Medication": "Aspirin",
        "Test Results": "Normal"
    }])

    # Day 1
    silver1 = scd2_merge(None, incoming, load_date="2024-06-01")

    # Day 2 — same incoming record
    silver2 = scd2_merge(silver1, incoming, load_date="2024-06-02")

    # No duplicate row inserted for unchanged record
    assert len(silver2) == 1
    assert silver2.iloc[0]["is_current"] == True


def test_scd2_merge_changed_record():
    day1_incoming = pd.DataFrame([{
        "Name": "Alice Brown",
        "Date of Admission": "2024-03-01",
        "Hospital": "St Jude",
        "Doctor": "Dr. House",
        "Billing Amount": 12000.00,
        "Room Number": 305,
        "Admission Type": "Elective",
        "Discharge Date": "2024-03-05",
        "Medication": "Aspirin",
        "Test Results": "Normal"
    }])

    # Day 1 initial load
    silver1 = scd2_merge(None, day1_incoming, load_date="2024-06-01")

    # Day 2 — updated Billing Amount and Test Results
    day2_incoming = pd.DataFrame([{
        "Name": "Alice Brown",
        "Date of Admission": "2024-03-01",
        "Hospital": "St Jude",
        "Doctor": "Dr. House",
        "Billing Amount": 14500.00,  # Changed
        "Room Number": 305,
        "Admission Type": "Elective",
        "Discharge Date": "2024-03-05",
        "Medication": "Aspirin",
        "Test Results": "Abnormal"  # Changed
    }])

    silver2 = scd2_merge(silver1, day2_incoming, load_date="2024-06-02")

    # Total rows = 2 (1 expired historical row + 1 current active row)
    assert len(silver2) == 2

    expired_row = silver2[silver2["is_current"] == False].iloc[0]
    active_row = silver2[silver2["is_current"] == True].iloc[0]

    # Check expired row attributes
    assert expired_row["Billing Amount"] == 12000.00
    assert expired_row["effective_start_date"] == "2024-06-01"
    assert expired_row["effective_end_date"] == "2024-06-02"

    # Check active row attributes
    assert active_row["Billing Amount"] == 14500.00
    assert active_row["Test Results"] == "Abnormal"
    assert active_row["effective_start_date"] == "2024-06-02"
    assert pd.isna(active_row["effective_end_date"]) or active_row["effective_end_date"] is None


def test_incremental_batch_processing(tmp_path):
    initial_batch = pd.DataFrame([
        {
            "Name": "Bobby Jackson", "Date of Admission": "2024-01-31", "Hospital": "Sons and Miller", "Doctor": "Matthew Smith",
            "Billing Amount": 18856.28, "Room Number": 328, "Admission Type": "Urgent", "Discharge Date": "2024-02-02",
            "Medication": "Paracetamol", "Test Results": "Normal"
        }
    ])

    # Initial load
    silver1 = scd2_merge(None, initial_batch, load_date="2024-06-01")
    assert len(silver1) == 1

    # Incremental batch: 1 update to Bobby Jackson + 1 brand new encounter
    incremental_batch = pd.DataFrame([
        {
            "Name": "Bobby Jackson", "Date of Admission": "2024-01-31", "Hospital": "Sons and Miller", "Doctor": "Matthew Smith",
            "Billing Amount": 19500.00, "Room Number": 328, "Admission Type": "Urgent", "Discharge Date": "2024-02-02",
            "Medication": "Paracetamol", "Test Results": "Abnormal"
        },
        {
            "Name": "Sarah Connor", "Date of Admission": "2024-06-01", "Hospital": "Metro Health", "Doctor": "Dr. Vance",
            "Billing Amount": 22400.00, "Room Number": 412, "Admission Type": "Elective", "Discharge Date": "2024-06-05",
            "Medication": "Lisinopril", "Test Results": "Normal"
        }
    ])

    silver2 = scd2_merge(silver1, incremental_batch, load_date="2024-06-02")

    # 1 new inserted + 1 changed + 1 expired -> Total rows = 3 (2 active, 1 expired)
    assert len(silver2) == 3

    # Ensure single active current record per encounter key
    current_df = silver2[silver2["is_current"] == True]
    assert len(current_df) == 2
    assert len(current_df["encounter_key"].unique()) == 2

