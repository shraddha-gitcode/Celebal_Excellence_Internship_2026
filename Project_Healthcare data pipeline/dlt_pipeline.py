"""Databricks Delta Live Tables (DLT) Declarative Pipeline Definition

Demonstrates automated Medallion Architecture (Bronze -> Silver -> Gold)
using Databricks DLT decorators (@dlt.table) and Data Quality Expectations (@dlt.expect).

Target Environment: Databricks Runtime for Delta Live Tables / Lakeflow Pipelines.
Note: This file is intended for execution within a Databricks DLT Pipeline workspace context.
"""
try:
    import dlt
    from pyspark.sql import functions as F
except ImportError:
    # Environment fallback when running outside Databricks DLT engine
    dlt = None

if dlt is not None:
    # -----------------------------------------------------------------------
    # BRONZE LAYER — Raw Ingestion Stream
    # -----------------------------------------------------------------------
    @dlt.table(
        name="dlt_healthcare_bronze",
        comment="Raw patient encounter records ingested into Bronze storage",
        table_properties={"quality": "bronze"}
    )
    def dlt_healthcare_bronze():
        return (
            dlt.read_stream("raw_patient_source")
            .withColumn("_ingestion_timestamp", F.current_timestamp())
            .withColumn("_source_file", F.input_file_name())
        )

    # -----------------------------------------------------------------------
    # SILVER LAYER — Cleaned & Standardized Stream with Expectations
    # -----------------------------------------------------------------------
    @dlt.table(
        name="dlt_healthcare_silver",
        comment="Cleaned and validated patient records with SCD Type 2 tracking",
        table_properties={"quality": "silver"}
    )
    @dlt.expect_or_drop("valid_name", "Name IS NOT NULL")
    @dlt.expect_or_drop("valid_admission_date", "Date_of_Admission IS NOT NULL")
    @dlt.expect("non_negative_billing", "Billing_Amount >= 0")
    def dlt_healthcare_silver():
        return (
            dlt.read_stream("dlt_healthcare_bronze")
            .withColumn("Name", F.initcap(F.trim(F.col("Name"))))
            .withColumn("Doctor", F.initcap(F.trim(F.col("Doctor"))))
            .withColumn("Hospital", F.initcap(F.trim(F.col("Hospital"))))
            .withColumn("Date_of_Admission", F.to_date(F.col("Date of Admission")))
            .withColumn("Billing_Amount", F.abs(F.round(F.col("Billing Amount").cast("double"), 2)))
            .withColumn("encounter_key", F.md5(F.concat_ws("|", F.col("Name"), F.col("Date_of_Admission"), F.col("Hospital"), F.col("Doctor"))))
        )

    # SCD Type 2 Change Data Capture (CDC) via DLT apply_changes
    dlt.create_streaming_table("dlt_healthcare_silver_scd2")
    dlt.apply_changes(
        target="dlt_healthcare_silver_scd2",
        source="dlt_healthcare_silver",
        keys=["encounter_key"],
        sequence_by=F.col("_ingestion_timestamp"),
        stored_as_scd_type=2
    )

    # -----------------------------------------------------------------------
    # GOLD LAYER — Aggregated Business Views
    # -----------------------------------------------------------------------
    @dlt.table(
        name="dlt_gold_hospital_ranking",
        comment="Hospital ranking by total billing revenue",
        table_properties={"quality": "gold"}
    )
    def dlt_gold_hospital_ranking():
        return (
            dlt.read("dlt_healthcare_silver_scd2")
            .filter("__is_current = true")
            .groupBy("Hospital")
            .agg(
                F.count("*").alias("patient_count"),
                F.round(F.sum("Billing_Amount"), 2).alias("total_billing"),
                F.round(F.avg("Billing_Amount"), 2).alias("avg_billing")
            )
            .orderBy(F.col("total_billing").desc())
        )
else:
    print("DLT module not available in local environment. Import skipped.")
