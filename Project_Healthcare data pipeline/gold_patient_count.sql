-- ============================================================================
-- Spark SQL: Patient Count per Hospital (Gold Layer)
-- Filters active records from SCD Type 2 Silver Delta table
-- ============================================================================

CREATE OR REPLACE TABLE healthcare_gold_patient_count AS
SELECT
    Hospital,
    COUNT(*) AS patient_count
FROM
    healthcare_silver
WHERE
    is_current = true
GROUP BY
    Hospital
ORDER BY
    patient_count DESC;
