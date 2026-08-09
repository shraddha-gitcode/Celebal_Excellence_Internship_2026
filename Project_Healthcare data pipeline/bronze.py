"""Databricks / PySpark Production Target — Bronze Layer Ingestion

Reads raw source CSV using Spark DataFrame API, appends ingestion metadata,
and writes to Delta Lake storage (`healthcare_bronze`).
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name

def run_bronze_pyspark(source_path: str = "/mnt/healthcare/source_data.csv",
                      delta_path: str = "/mnt/delta/healthcare_bronze",
                      table_name: str = "healthcare_bronze"):
    """Ingests raw CSV data into Delta Lake Bronze table without mutating business columns."""
    spark = SparkSession.builder \
        .appName("HealthcarePipeline-Bronze") \
        .getOrCreate()

    # Read raw dataset with string schema enforcement
    raw_df = spark.read.format("csv") \
        .option("header", "true") \
        .option("inferSchema", "false") \
        .load(source_path)

    # Append ingestion metadata columns
    bronze_df = raw_df \
        .withColumn("_ingestion_timestamp", current_timestamp()) \
        .withColumn("_source_file", input_file_name())

    # Write as Delta table (Append mode for batch ingestion)
    bronze_df.write.format("delta") \
        .mode("append") \
        .option("mergeSchema", "true") \
        .save(delta_path)

    # Save to catalog/metastore if configured
    spark.sql(f"CREATE TABLE IF NOT EXISTS {table_name} USING DELTA LOCATION '{delta_path}'")

    print(f"Successfully ingested {bronze_df.count()} rows into Bronze table '{table_name}'.")

if __name__ == "__main__":
    run_bronze_pyspark()
