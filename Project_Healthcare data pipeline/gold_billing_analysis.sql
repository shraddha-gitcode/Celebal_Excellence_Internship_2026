-- ============================================================================
-- Spark SQL: Billing Breakdown by Admission Type & Insurance Provider (Gold Layer)
-- Multi-dimensional aggregation for BI financial reporting
-- ============================================================================

-- 1. Billing by Admission Type
CREATE OR REPLACE TABLE healthcare_gold_billing_admission AS
SELECT
    `Admission Type`,
    COUNT(*) AS patient_count,
    ROUND(AVG(`Billing Amount`), 2) AS avg_billing,
    ROUND(SUM(`Billing Amount`), 2) AS total_billing
FROM
    healthcare_silver
WHERE
    is_current = true
GROUP BY
    `Admission Type`
ORDER BY
    total_billing DESC;

-- 2. Billing by Insurance Provider
CREATE OR REPLACE TABLE healthcare_gold_billing_insurance AS
SELECT
    `Insurance Provider`,
    COUNT(*) AS patient_count,
    ROUND(AVG(`Billing Amount`), 2) AS avg_billing,
    ROUND(SUM(`Billing Amount`), 2) AS total_billing
FROM
    healthcare_silver
WHERE
    is_current = true
GROUP BY
    `Insurance Provider`
ORDER BY
    total_billing DESC;
