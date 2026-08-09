-- ============================================================================
-- Spark SQL: Hospital Ranking by Revenue & Billing Metrics (Gold Layer)
-- Demonstrates Window Ranking Functions & Aggregations
-- ============================================================================

CREATE OR REPLACE TABLE healthcare_gold_hospital_ranking AS
WITH HospitalMetrics AS (
    SELECT
        Hospital,
        COUNT(*) AS patient_count,
        ROUND(SUM(`Billing Amount`), 2) AS total_billing,
        ROUND(AVG(`Billing Amount`), 2) AS avg_billing
    FROM
        healthcare_silver
    WHERE
        is_current = true
    GROUP BY
        Hospital
)
SELECT
    RANK() OVER (ORDER BY total_billing DESC) AS rank,
    Hospital,
    patient_count,
    total_billing,
    avg_billing
FROM
    HospitalMetrics
ORDER BY
    rank ASC;
