"""
Week 5 — Spark Fundamentals: Data Cleaning, Transformation & Aggregation
Full runnable PySpark pipeline on a synthetic, intentionally messy sales dataset.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

spark = (
    SparkSession.builder
    .appName("Week5-Spark-Fundamentals")
    .master("local[*]")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

print("=" * 80)
print("STEP 1: LOAD RAW DATA WITH AN EXPLICIT SCHEMA (avoiding inferSchema risk)")
print("=" * 80)

# Explicit schema instead of inferSchema=True -> avoids silently mis-typed/mis-parsed
# columns, especially for the date/timestamp fields (see Q14 insight).
schema = StructType([
    StructField("user_id", StringType(), True),
    StructField("transaction_date", StringType(), True),
    StructField("store_id", StringType(), True),
    StructField("city", StringType(), True),
    StructField("region", StringType(), True),
    StructField("product_category", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("subscription", StringType(), True),
    StructField("sale_amount", DoubleType(), True),
    StructField("status", StringType(), True),
    StructField("raw_timestamp", StringType(), True),
    StructField("email", StringType(), True),
    StructField("username", StringType(), True),
])

df_raw = spark.read.csv("raw_sales.csv", header=True, schema=schema)

print(f"Raw row count: {df_raw.count()}")
df_raw.printSchema()

print("=" * 80)
print("STEP 2: DATA CLEANING - remove duplicates, handle nulls, handle empty strings")
print("=" * 80)

# 2a. Remove exact duplicate transactions keyed on user_id + transaction_date
df_dedup = df_raw.dropDuplicates(["user_id", "transaction_date"])
print(f"Rows after dropDuplicates(user_id, transaction_date): {df_dedup.count()} "
      f"(removed {df_raw.count() - df_dedup.count()} duplicate rows)")

# 2b. Handle nulls:
#   - sale_amount: fill missing sale amounts with 0 (a missing amount != skip the row)
#   - status: fill missing status with 'Unknown'
#   - age: fill missing age with the column median (robust to outliers) computed on non-null rows
median_age = df_dedup.approxQuantile("age", [0.5], 0.01)[0]
df_filled = df_dedup.na.fill({
    "sale_amount": 0.0,
    "status": "Unknown",
    "age": int(median_age),
})
print(f"Median age used to fill null ages: {int(median_age)}")

# 2c. Remove rows with unusable identity fields: null email OR empty/whitespace username
before = df_filled.count()
df_clean = df_filled.filter(
    F.col("email").isNotNull() & (F.trim(F.col("username")) != "")
)
print(f"Rows after removing null-email / empty-username rows: {df_clean.count()} "
      f"(removed {before - df_clean.count()} rows)")

print("=" * 80)
print("STEP 3: SCHEMA MODIFICATION - casting & renaming columns")
print("=" * 80)

# Cast raw_timestamp (string) -> TimestampType, rename to event_time
df_clean = (
    df_clean
    .withColumn("event_time", F.to_timestamp(F.col("raw_timestamp"), "yyyy-MM-dd HH:mm:ss"))
    .drop("raw_timestamp")
    .withColumnRenamed("sale_amount", "revenue")
)

df_clean.printSchema()
df_clean.select("event_time", "revenue").show(5, truncate=False)

print("=" * 80)
print("STEP 4: FILTERING - age range, category, region conditions")
print("=" * 80)

# Filter: age between 18 and 30 (inclusive) AND subscription == 'Premium'
df_young_premium = df_clean.filter(
    F.col("age").between(18, 30) & (F.col("subscription") == "Premium")
)
print(f"Rows with age 18-30 AND Premium subscription: {df_young_premium.count()}")
df_young_premium.select("user_id", "age", "subscription", "region").show(5)

# Filter: region == 'West'
df_west = df_clean.filter(F.col("region") == "West")
print(f"Rows in region = 'West': {df_west.count()}")

print("=" * 80)
print("STEP 5: AGGREGATION - avg revenue by category, filtered to West region")
print("=" * 80)

west_avg_by_category = (
    df_west
    .groupBy("product_category")
    .agg(
        F.count("*").alias("num_transactions"),
        F.round(F.avg("revenue"), 2).alias("avg_revenue"),
        F.round(F.sum("revenue"), 2).alias("total_revenue"),
        F.round(F.min("revenue"), 2).alias("min_revenue"),
        F.round(F.max("revenue"), 2).alias("max_revenue"),
    )
    .orderBy(F.col("avg_revenue").desc())
)
west_avg_by_category.show(truncate=False)

print("=" * 80)
print("STEP 6: GROUPBY WITH HAVING-STYLE CONDITION ON AGGREGATED RESULT")
print("=" * 80)

# Count of transactions per city, only cities with more than 15 transactions
city_counts = (
    df_clean.groupBy("city")
    .count()
    .filter(F.col("count") > 15)
    .orderBy(F.col("count").desc())
)
city_counts.show(truncate=False)

print("=" * 80)
print("STEP 7: WIDE TRANSFORMATION / SHUFFLE DEMONSTRATION")
print("=" * 80)

print(f"Number of partitions BEFORE groupBy: {df_clean.rdd.getNumPartitions()}")
grouped = df_clean.groupBy("region").agg(F.sum("revenue").alias("total_revenue"))
print(f"Number of partitions AFTER groupBy (post-shuffle, default spark.sql.shuffle.partitions): "
      f"{grouped.rdd.getNumPartitions()}")
grouped.explain(mode="formatted")

print("=" * 80)
print("STEP 8: FULL PIPELINE - dedupe -> fill nulls -> group by store_id -> total revenue")
print("=" * 80)

final_pipeline_result = (
    df_raw
    .dropDuplicates(["user_id", "transaction_date"])      # 1. remove duplicates
    .na.fill({"sale_amount": 0.0})                        # 2. fill null revenue with 0
    .groupBy("store_id")
    .agg(F.round(F.sum("sale_amount"), 2).alias("total_revenue"))  # 3. total revenue per store
    .orderBy(F.col("total_revenue").desc())
)

final_pipeline_result.show(10, truncate=False)

print("=" * 80)
print("DONE")
print("=" * 80)

spark.stop()
