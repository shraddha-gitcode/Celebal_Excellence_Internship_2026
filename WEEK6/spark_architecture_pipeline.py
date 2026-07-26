"""
Spark Architecture & Efficient Data Processing — Full Pipeline
Demonstrates: architecture, lazy evaluation/DAG, schema handling, filtering,
column transforms, wide transformations/shuffle, predicate pushdown,
CSV vs Parquet performance, and read -> transform -> filter -> write pipeline.
"""

import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

spark = (
    SparkSession.builder
    .appName("Spark-Architecture-Pipeline")
    .master("local[*]")          # execution mode: local, all cores -> Driver + Executors in one JVM
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

print("=" * 80)
print("SPARK ARCHITECTURE INFO (Driver / Cluster Manager / Executors)")
print("=" * 80)
sc = spark.sparkContext
print(f"Master (cluster manager URL): {sc.master}")
print(f"Application ID (Driver-assigned): {sc.applicationId}")
print(f"Default parallelism (executor cores available): {sc.defaultParallelism}")
# In local[*] mode, the Driver and Executor(s) run in the SAME JVM process.
# In cluster mode (YARN/Kubernetes/Standalone), the Driver runs the DAG scheduler
# and negotiates resources from the Cluster Manager, which launches separate
# Executor JVMs on worker nodes to actually run tasks.

print("=" * 80)
print("STEP 1: READ CSV WITH EXPLICIT SCHEMA (avoid inferSchema on large files)")
print("=" * 80)

schema = StructType([
    StructField("emp_id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("department", StringType(), True),
    StructField("country", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("salary", DoubleType(), True),
    StructField("join_date", StringType(), True),
    StructField("status", StringType(), True),
    StructField("email", StringType(), True),
])

df_csv = spark.read.csv("employees.csv", header=True, schema=schema)
print(f"Row count (CSV read): {df_csv.count()}")
df_csv.printSchema()

print("=" * 80)
print("STEP 2: LAZY EVALUATION DEMONSTRATION")
print("=" * 80)

# Transformations below are NOT executed yet -- Spark only builds a logical plan.
t0 = time.time()
lazy_chain = (
    df_csv
    .filter(F.col("salary").isNotNull())
    .withColumn("bonus", F.col("salary") * 0.1)
    .select("emp_id", "department", "salary", "bonus")
)
build_time = time.time() - t0
print(f"Time to BUILD the transformation chain (no action yet): {build_time:.4f}s "
      f"(near-instant because nothing has executed)")

t0 = time.time()
result_count = lazy_chain.count()   # <- this is the ACTION that triggers execution
exec_time = time.time() - t0
print(f"Time to EXECUTE via .count() action: {exec_time:.4f}s -> {result_count} rows")
print("This gap illustrates lazy evaluation: transformations only describe *what* "
      "to do; Spark builds a DAG/lineage graph and only computes it when an action runs.")

print("\nLogical + physical plan (lineage) for the chain above:")
lazy_chain.explain(mode="extended")

print("=" * 80)
print("STEP 3: SCHEMA MODIFICATION - rename, cast, add column")
print("=" * 80)

df_transformed = (
    df_csv
    .withColumnRenamed("emp_id", "employee_id")
    .withColumn("join_date", F.to_date(F.col("join_date"), "yyyy-MM-dd"))
    .withColumn("salary_band", F.when(F.col("salary") >= 100000, "High")
                                  .when(F.col("salary") >= 60000, "Mid")
                                  .otherwise("Low"))
)
df_transformed.printSchema()
df_transformed.select("employee_id", "join_date", "salary", "salary_band").show(5)

print("=" * 80)
print("STEP 4: NULL HANDLING + EFFICIENT FILTERING")
print("=" * 80)

before = df_transformed.count()
df_clean = (
    df_transformed
    .na.drop(subset=["email"])                 # drop rows with no email (unusable identity)
    .na.fill({"age": 0, "status": "Unknown"})   # fill rather than drop where recoverable
)
print(f"Rows before null handling: {before} | after: {df_clean.count()}")

# Filter selection: only Active employees earning above 60000, in specific countries
df_filtered = (
    df_clean
    .filter(
        (F.col("status") == "Active")
        & (F.col("salary") > 60000)
        & (F.col("country").isin("USA", "India", "Germany"))
    )
    .select("employee_id", "name", "department", "country", "salary", "salary_band")
)
print(f"Filtered result count: {df_filtered.count()}")
df_filtered.show(5)   # best practice: .show() for inspection, NEVER collect() on full data

print("=" * 80)
print("STEP 5: WIDE TRANSFORMATION / SHUFFLE - avg salary by department")
print("=" * 80)

dept_avg = (
    df_clean.groupBy("department")
    .agg(
        F.count("*").alias("headcount"),
        F.round(F.avg("salary"), 2).alias("avg_salary"),
    )
    .orderBy(F.col("avg_salary").desc())
)
dept_avg.show()
print("groupBy triggers a shuffle (Exchange) -> confirmed via explain():")
dept_avg.explain()

print("=" * 80)
print("STEP 6: WRITE TO PARQUET AND CSV, THEN COMPARE")
print("=" * 80)

df_clean.write.mode("overwrite").parquet("employees_parquet")
df_clean.write.mode("overwrite").option("header", True).csv("employees_csv_out")

import subprocess
parquet_size = subprocess.run(["du", "-sh", "employees_parquet"], capture_output=True, text=True).stdout
csv_size = subprocess.run(["du", "-sh", "employees_csv_out"], capture_output=True, text=True).stdout
print(f"Parquet output size: {parquet_size.strip()}")
print(f"CSV output size:     {csv_size.strip()}")

print("=" * 80)
print("STEP 7: PREDICATE PUSHDOWN - CSV vs PARQUET read+filter timing")
print("=" * 80)

# Re-read both, apply an identical filter, and compare explain() + timing.
# Parquet is a columnar, splittable format that supports predicate pushdown:
# Spark can skip entire row-groups/files based on min/max stats without
# reading all columns, unlike row-based CSV which must scan every row/column.

t0 = time.time()
df_from_csv = spark.read.csv("employees_csv_out", header=True, inferSchema=True)
csv_filtered = df_from_csv.filter(F.col("department") == "Engineering").select("employee_id", "salary")
csv_count = csv_filtered.count()
csv_time = time.time() - t0

t0 = time.time()
df_from_parquet = spark.read.parquet("employees_parquet")
parquet_filtered = df_from_parquet.filter(F.col("department") == "Engineering").select("employee_id", "salary")
parquet_count = parquet_filtered.count()
parquet_time = time.time() - t0

print(f"CSV read+filter:     {csv_count} rows in {csv_time:.4f}s")
print(f"Parquet read+filter: {parquet_count} rows in {parquet_time:.4f}s")

print("\nParquet physical plan (look for PushedFilters in the scan node):")
parquet_filtered.explain()

print("\nCSV physical plan (CSV source shows NO effective PushedFilters -- full row scan):")
csv_filtered.explain()

print("=" * 80)
print("STEP 8: FULL PIPELINE - read -> transform -> filter -> write (Parquet)")
print("=" * 80)

final_output = (
    spark.read.csv("employees.csv", header=True, schema=schema)      # READ
    .withColumnRenamed("emp_id", "employee_id")                      # TRANSFORM (rename)
    .withColumn("join_date", F.to_date(F.col("join_date"), "yyyy-MM-dd"))  # TRANSFORM (cast)
    .na.drop(subset=["email"])                                       # CLEAN
    .na.fill({"age": 0, "status": "Unknown"})                        # CLEAN
    .filter((F.col("status") == "Active") & (F.col("salary") > 60000))    # FILTER
    .select("employee_id", "name", "department", "country", "age", "salary", "join_date", "status")
)

final_output.write.mode("overwrite").parquet("final_pipeline_output")
print(f"Final pipeline output row count: {final_output.count()}")
final_output.show(5)
print("Written to: final_pipeline_output/ (Parquet)")

print("=" * 80)
print("DONE")
print("=" * 80)

spark.stop()
