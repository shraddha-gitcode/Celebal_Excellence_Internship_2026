# Technical Architecture — Healthcare Data Pipeline

## Overview

This project implements an enterprise-grade healthcare data pipeline based on the **Medallion Architecture** pattern (Bronze → Silver → Gold).

```
                      MEDALLION ARCHITECTURE PIPELINE
                      
  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
  │  Source Data   │ ──> │  Bronze Layer  │ ──> │  Silver Layer  │ ──> │   Gold Layer   │
  │ (Raw Patient   │     │ (Raw Storage & │     │ (Cleaned & SCD │     │  (Aggregated   │
  │  Records CSV)  │     │   Lineage)     │     │  Type 2 MERGE) │     │  BI Datasets)  │
  └────────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
                                                                               │
                                                                               ▼
                                                                      ┌────────────────┐
                                                                      │   BI / HTML    │
                                                                      │   Dashboard    │
                                                                      └────────────────┘
```

---

## Medallion Layer Design

### 1. Bronze Layer (Raw Preservation)
- **Goal**: Preserve raw source datasets exactly as received for complete auditability, lineage, and operational re-processing.
- **Transformations**: No business transformations applied. String-coerced extraction preserves exact raw string values.
- **Metadata Added**:
  - `_ingestion_timestamp` (UTC ISO string)
  - `_source_file` (Origin file basename)
  - `_bronze_row_id` (Monotonically increasing sequence key)

### 2. Silver Layer (Cleaned & Standardized + SCD Type 2 MERGE)
- **Goal**: Provide clean, deduplicated, standardized patient encounter records with full historical change tracking.
- **Standardization**:
  - Text whitespace trimming & Title Case normalization (`Name`, `Doctor`, `Hospital`, `Medical Condition`, etc.).
  - ISO Date formatting (`YYYY-MM-DD`).
  - Integer casting for `Age` and `Room Number`; Rounding `Billing Amount` to 2 decimal places.
  - Data Quality audit flag `_dq_negative_billing` for negative amounts, normalizing value using absolute magnitude `.abs()`.
  - Exact duplicate row removal and null handling for critical business columns (`Name`, `Date of Admission`, `Hospital`, `Billing Amount`).
- **SCD Type 2 MERGE Logic**:
  - **Business Key**: `MD5(Name | Date of Admission | Hospital | Doctor)`
  - **Tracked Attributes Hash**: `MD5(Billing Amount | Room Number | Admission Type | Discharge Date | Medication | Test Results)`
  - **Behavior**:
    - New `encounter_key` → Insert record as current active version (`is_current = True`, `effective_start_date = load_date`).
    - Existing key + unchanged hash diff → No-op.
    - Existing key + changed hash diff → Expire old record (`is_current = False`, `effective_end_date = load_date`) and insert new current version (`is_current = True`, `effective_start_date = load_date`).
  - **Constraint**: Exactly one active record (`is_current == True`) per `encounter_key`.

### 3. Gold Layer (BI Aggregations & Analytics)
- **Goal**: Deliver high-performance, business-ready tables for executive dashboards and reporting tools.
- **Scope**: Queries **only** current active records (`is_current = True`) from the Silver layer.
- **Aggregated Datasets**:
  1. `patient_count_per_hospital`: Total active patient encounters per facility.
  2. `hospital_ranking`: Ranked hospital performance by total billing revenue and average billing per patient.
  3. `contribution_by_medical_condition`: Patient counts, percentage share, total revenue, and average cost by primary diagnosis.
  4. `billing_by_admission_type`: Cost breakdown across Elective, Emergency, and Urgent admissions.
  5. `billing_by_insurance_provider`: Revenue contribution across insurance payors.
  6. `monthly_admission_trend`: Time-series admission volume by month.
  7. `test_outcomes_by_condition`: Outcome distribution (Normal, Abnormal, Inconclusive) by medical condition (foundation for risk modeling).
  8. `demographics_by_age_group`: Demographic distribution across standard medical age brackets (`0-18`, `19-30`, `31-45`, `46-60`, `61-75`, `76+`).

---

## Dual Implementation Model

| Aspect | Local Python Implementation (`src/`) | Databricks Production Implementation (`databricks/`) |
| :--- | :--- | :--- |
| **Purpose** | Local development, CI/CD automated testing, offline reproduction | Cloud enterprise scale, big data execution |
| **Engine** | Python 3 + Pandas | PySpark DataFrames + Spark SQL |
| **Storage Format** | Standard CSV + JSON snapshots | Delta Lake tables (ACID transactions, time travel) |
| **SCD2 Logic** | Custom vectorized Pandas `scd2_merge()` | Delta Lake `DeltaTable.merge()` & DLT `dlt.apply_changes()` |
| **Execution Command** | `python src/pipeline.py` | Databricks Workflow / DLT Pipeline Job |

---

## Data Quality Framework

Strict validation rules are implemented across all pipeline stages:
1. **Bronze Validation**: Asserts non-empty dataset and presence of lineage metadata columns.
2. **Silver Validation**: Asserts zero nulls in critical business fields, verifies negative billing correction flags, and enforces single active record uniqueness per `encounter_key`.
3. **Gold Validation**: Asserts non-empty output dataframes across all 8 business tables.
