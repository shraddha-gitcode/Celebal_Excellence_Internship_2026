"""Databricks / PySpark Production Target — Gold Layer Aggregations

Queries current active encounters from Silver Delta table (`is_current = true`)
and creates BI-ready Gold aggregated Delta tables.
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def run_gold_pyspark(silver_table: str = "healthcare_silver"):
    """Builds Gold aggregated Delta tables from active Silver records."""
    spark = SparkSession.builder \
        .appName("HealthcarePipeline-Gold") \
        .getOrCreate()

    # Query active records only
    silver_df = spark.table(silver_table).filter("is_current = true")

    # 1. Patient Count per Hospital
    patient_count_df = silver_df.groupBy("Hospital") \
        .agg(F.count("*").alias("patient_count")) \
        .orderBy(F.col("patient_count").desc())
    patient_count_df.write.format("delta").mode("overwrite").saveAsTable("healthcare_gold_patient_count")

    # 2. Hospital Ranking
    ranking_df = silver_df.groupBy("Hospital") \
        .agg(
            F.count("*").alias("patient_count"),
            F.round(F.sum("Billing Amount"), 2).alias("total_billing"),
            F.round(F.avg("Billing Amount"), 2).alias("avg_billing")
        ).orderBy(F.col("total_billing").desc())
    ranking_df.write.format("delta").mode("overwrite").saveAsTable("healthcare_gold_hospital_ranking")

    # 3. Medical Condition Analysis
    condition_df = silver_df.groupBy("Medical Condition") \
        .agg(
            F.count("*").alias("patient_count"),
            F.round(F.avg("Billing Amount"), 2).alias("avg_billing"),
            F.round(F.sum("Billing Amount"), 2).alias("total_billing")
        ).orderBy(F.col("patient_count").desc())
    condition_df.write.format("delta").mode("overwrite").saveAsTable("healthcare_gold_condition")

    # 4. Billing by Admission Type
    billing_admission_df = silver_df.groupBy("Admission Type") \
        .agg(
            F.count("*").alias("patient_count"),
            F.round(F.avg("Billing Amount"), 2).alias("avg_billing"),
            F.round(F.sum("Billing Amount"), 2).alias("total_billing")
        )
    billing_admission_df.write.format("delta").mode("overwrite").saveAsTable("healthcare_gold_billing_admission")

    # 5. Billing by Insurance Provider
    insurance_df = silver_df.groupBy("Insurance Provider") \
        .agg(
            F.count("*").alias("patient_count"),
            F.round(F.avg("Billing Amount"), 2).alias("avg_billing"),
            F.round(F.sum("Billing Amount"), 2).alias("total_billing")
        ).orderBy(F.col("total_billing").desc())
    insurance_df.write.format("delta").mode("overwrite").saveAsTable("healthcare_gold_billing_insurance")

    print("Gold Delta tables successfully created in Databricks metastore.")

if __name__ == "__main__":
    run_gold_pyspark()
