-- ============================================================================
-- Spark SQL: Medical Condition Analysis & Patient Percentage (Gold Layer)
-- Calculates distribution across primary diagnoses
-- ============================================================================

CREATE OR REPLACE TABLE healthcare_gold_condition AS
WITH TotalPatients AS (
    SELECT COUNT(*) AS total_count FROM healthcare_silver WHERE is_current = true
)
SELECT
    s.`Medical Condition`,
    COUNT(*) AS patient_count,
    ROUND((COUNT(*) * 100.0 / t.total_count), 2) AS pct_of_patients,
    ROUND(AVG(s.`Billing Amount`), 2) AS avg_billing,
    ROUND(SUM(s.`Billing Amount`), 2) AS total_billing
FROM
    healthcare_silver s
CROSS JOIN
    TotalPatients t
WHERE
    s.is_current = true
GROUP BY
    s.`Medical Condition`, t.total_count
ORDER BY
    patient_count DESC;
