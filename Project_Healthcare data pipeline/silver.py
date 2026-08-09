"""Databricks / PySpark Production Target — Silver Layer & SCD Type 2 MERGE

Standardizes text casing, dates, numeric fields, flags data quality issues,
and performs Delta Lake `MERGE INTO` statement to track SCD Type 2 history.
"""
from delta.tables import DeltaTable
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def run_silver_pyspark(bronze_table: str = "healthcare_bronze",
                       silver_path: str = "/mnt/delta/healthcare_silver",
                       silver_table: str = "healthcare_silver"):
    """Transforms Bronze dataset and performs SCD Type 2 MERGE into Silver Delta table."""
    spark = SparkSession.builder \
        .appName("HealthcarePipeline-Silver") \
        .getOrCreate()

    bronze_df = spark.table(bronze_table)

    # Standardize string fields (Trim & Title Case)
    cleaned_df = bronze_df \
        .withColumn("Name", F.initcap(F.trim(F.col("Name")))) \
        .withColumn("Doctor", F.initcap(F.trim(F.col("Doctor")))) \
        .withColumn("Hospital", F.initcap(F.trim(F.col("Hospital")))) \
        .withColumn("Gender", F.initcap(F.trim(F.col("Gender")))) \
        .withColumn("Medical Condition", F.initcap(F.trim(F.col("Medical Condition")))) \
        .withColumn("Admission Type", F.initcap(F.trim(F.col("Admission Type")))) \
        .withColumn("Test Results", F.initcap(F.trim(F.col("Test Results")))) \

    # Standardize dates & numbers
    cleaned_df = cleaned_df \
        .withColumn("Date of Admission", F.to_date(F.col("Date of Admission"))) \
        .withColumn("Discharge Date", F.to_date(F.col("Discharge Date"))) \
        .withColumn("Age", F.col("Age").cast("integer")) \
        .withColumn("Room Number", F.col("Room Number").cast("integer")) \
        .withColumn("Billing Amount", F.round(F.col("Billing Amount").cast("double"), 2))

    # Flag negative billing
    cleaned_df = cleaned_df \
        .withColumn("_dq_negative_billing", F.col("Billing Amount") < 0) \
        .withColumn("Billing Amount", F.abs(F.col("Billing Amount")))

    # Filter nulls in critical fields & exact duplicates
    cleaned_df = cleaned_df.dropna(subset=["Name", "Date of Admission", "Hospital", "Billing Amount"]) \
        .dropDuplicates(["Name", "Date of Admission", "Hospital", "Doctor", "Billing Amount"])

    # Compute MD5 Business Key & Hash Diff for SCD2 tracking
    incoming = cleaned_df \
        .withColumn("encounter_key", F.md5(F.concat_ws("|", F.col("Name"), F.col("Date of Admission"), F.col("Hospital"), F.col("Doctor")))) \
        .withColumn("hash_diff", F.md5(F.concat_ws("|", F.col("Billing Amount"), F.col("Room Number"), F.col("Admission Type"), F.col("Discharge Date"), F.col("Medication"), F.col("Test Results"))))

    # Check if target Silver Delta table exists
    if not spark.catalog.tableExists(silver_table):
        # Initial Load
        initial_target = incoming \
            .withColumn("effective_start_date", F.current_date()) \
            .withColumn("effective_end_date", F.lit(None).cast("date")) \
            .withColumn("is_current", F.lit(True)) \
            .withColumn("_scd_surrogate_key", F.monotonically_increasing_id())

        initial_target.write.format("delta").mode("overwrite").save(silver_path)
        spark.sql(f"CREATE TABLE IF NOT EXISTS {silver_table} USING DELTA LOCATION '{silver_path}'")
        print(f"Created initial Silver table '{silver_table}'.")
        return

    # Incremental SCD Type 2 Delta MERGE
    target_table = DeltaTable.forName(spark, silver_table)

    # 1. Expire existing records where tracked attributes changed
    target_table.alias("target").merge(
        source=incoming.alias("source"),
        condition="target.encounter_key = source.encounter_key AND target.is_current = true AND target.hash_diff != source.hash_diff"
    ).whenMatchedUpdate(set={
        "is_current": "false",
        "effective_end_date": "current_date()"
    }).execute()

    # 2. Insert new encounters & new current versions of updated encounters
    updated_staged = incoming.alias("source").join(
        target_table.toDF().alias("target"),
        on=(F.col("source.encounter_key") == F.col("target.encounter_key")) & (F.col("target.is_current") == True),
        how="left"
    ).filter(
        (F.col("target.encounter_key").isNull()) | (F.col("source.hash_diff") != F.col("target.hash_diff"))
    ).select("source.*") \
     .withColumn("effective_start_date", F.current_date()) \
     .withColumn("effective_end_date", F.lit(None).cast("date")) \
     .withColumn("is_current", F.lit(True)) \
     .withColumn("_scd_surrogate_key", F.monotonically_increasing_id())

    updated_staged.write.format("delta").mode("append").save(silver_path)
    print(f"SCD Type 2 MERGE successfully executed on Silver table '{silver_table}'.")

if __name__ == "__main__":
    run_silver_pyspark()
