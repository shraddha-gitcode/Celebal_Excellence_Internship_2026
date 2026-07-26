# Spark Architecture & Efficient Data Processing — Full Pipeline

A runnable PySpark pipeline executed against a synthetic 2,000-row employee
dataset, demonstrating Spark's architecture, lazy evaluation/DAG, schema
handling, filtering, wide transformations/shuffle, and CSV vs. Parquet
performance (including predicate pushdown). Every result below is **actual
output** from running the script.

**Files:**
- `spark_architecture_pipeline.py` — the complete runnable script
- This report — walkthrough + real execution results + insights

---

## 1. Spark Architecture: Driver, Cluster Manager, Executors

```python
spark = SparkSession.builder.appName("Spark-Architecture-Pipeline").master("local[*]").getOrCreate()
sc = spark.sparkContext
print(sc.master, sc.applicationId, sc.defaultParallelism)
```

**Actual output:**
```
Master (cluster manager URL): local[*]
Application ID (Driver-assigned): local-1785067714397
Default parallelism (executor cores available): 1
```

**How the three pieces fit together:**

| Component | Role |
|---|---|
| **Driver** | Runs the `SparkSession`/`SparkContext`, builds the logical plan, converts it into a DAG of stages/tasks via the DAG scheduler, and coordinates execution. This script's Python process *is* the Driver. |
| **Cluster Manager** | Negotiates and allocates resources (CPU/memory) for the application. Options: **Standalone**, **YARN**, **Kubernetes**, or — as used here — the built-in **local** manager (`local[*]`, using all local cores in a single JVM). |
| **Executors** | JVM processes on worker nodes that actually run tasks and hold cached data/shuffle files. In `local[*]` mode the Driver and Executor share the same JVM; in a real cluster they're separate processes on separate machines. |

**Execution modes:** `local[*]` (single machine, dev/test — used here), `client` (Driver runs on the machine that submits the job, Executors on the cluster), and `cluster` (Driver itself runs *inside* the cluster, managed by YARN/Kubernetes) — the latter two are standard for production jobs.

---

## 2. Lazy Evaluation & DAG (Lineage Graph)

```python
lazy_chain = (
    df_csv
    .filter(F.col("salary").isNotNull())
    .withColumn("bonus", F.col("salary") * 0.1)
    .select("emp_id", "department", "salary", "bonus")
)
# no execution yet...
result_count = lazy_chain.count()   # <- ACTION triggers execution
```

**Actual output:**
```
Time to BUILD the transformation chain (no action yet): 0.1826s
Time to EXECUTE via .count() action: 0.8128s -> 1916 rows
```

Building the chain (`filter` → `withColumn` → `select`) took almost no time because **nothing ran** — Spark only recorded the operations as a logical plan. The real computation happened only when `.count()` (an **action**) was called.

**The lineage/DAG for this chain** (`explain(mode="extended")`), shown across its optimization phases:

```
== Optimized Logical Plan ==
Project [emp_id#0, department#2, salary#5, (salary#5 * 0.1) AS bonus#23]
+- Filter isnotnull(salary#5)
   +- Relation [emp_id#0,name#1,...] csv

== Physical Plan ==
*(1) Project [emp_id#0, department#2, salary#5, (salary#5 * 0.1) AS bonus#23]
+- *(1) Filter isnotnull(salary#5)
   +- FileScan csv [emp_id#0,department#2,salary#5]
      PushedFilters: [IsNotNull(salary)]
      ReadSchema: struct<emp_id:string,department:string,salary:double>
```

Two optimizations are visible directly in this plan:
- **Column pruning** — `ReadSchema` only reads `emp_id`, `department`, `salary` (not `name`, `country`, `join_date`, etc.), even though the source CSV has 9 columns.
- **Predicate pushdown** — `PushedFilters: [IsNotNull(salary)]` shows the null-filter was pushed down into the scan itself rather than applied afterward.

This is the concrete payoff of **lazy evaluation**: Spark sees the *entire* chain before running anything, so its Catalyst optimizer can rewrite/reorder/merge operations (like pushing the filter into the scan) for a single efficient physical plan — something a Driver executing each line eagerly could never do.

---

## 3. Schema Modification — Rename, Cast, Add Column

```python
df_transformed = (
    df_csv
    .withColumnRenamed("emp_id", "employee_id")
    .withColumn("join_date", F.to_date(F.col("join_date"), "yyyy-MM-dd"))
    .withColumn("salary_band", F.when(F.col("salary") >= 100000, "High")
                                  .when(F.col("salary") >= 60000, "Mid")
                                  .otherwise("Low"))
)
```

**Actual resulting schema:**
```
root
 |-- employee_id: string        <- renamed from emp_id
 |-- name: string
 |-- department: string
 |-- country: string
 |-- age: integer
 |-- salary: double
 |-- join_date: date            <- cast from string
 |-- status: string
 |-- email: string
 |-- salary_band: string        <- new derived column
```

**Sample rows:**
```
+-----------+----------+---------+-----------+
|employee_id| join_date|   salary|salary_band|
+-----------+----------+---------+-----------+
|     E10000|2024-01-17|112702.89|       High|
|     E10001|2018-11-21| 96555.28|        Mid|
|     E10002|2019-07-05| 41754.49|        Low|
|     E10003|2020-02-18|117824.64|       High|
|     E10004|2022-10-15| 97000.88|        Mid|
+-----------+----------+---------+-----------+
```

Every call above returns a **new** DataFrame (immutability) — `df_csv` itself is never modified.

---

## 4. Null Handling & Efficient Filtering

```python
df_clean = (
    df_transformed
    .na.drop(subset=["email"])
    .na.fill({"age": 0, "status": "Unknown"})
)

df_filtered = (
    df_clean
    .filter(
        (F.col("status") == "Active")
        & (F.col("salary") > 60000)
        & (F.col("country").isin("USA", "India", "Germany"))
    )
    .select("employee_id", "name", "department", "country", "salary", "salary_band")
)
```

**Actual output:**
```
Rows before null handling: 2000 | after: 1926     (74 rows dropped: missing email)
Filtered result count: 192
+-----------+-----------+-----------+-------+---------+-----------+
|employee_id|       name| department|country|   salary|salary_band|
+-----------+-----------+-----------+-------+---------+-----------+
|     E10015|Employee_15|Engineering|    USA| 87723.44|        Mid|
|     E10017|Employee_17|      Sales|    USA|135348.23|       High|
|     E10023|Employee_23|    Support|  India|127197.12|       High|
|     E10035|Employee_35|         HR|Germany|139711.87|       High|
|     E10061|Employee_61|  Marketing|Germany| 63382.46|        Mid|
+-----------+-----------+-----------+-------+---------+-----------+
```

Used `.show()` for inspection here — **never `.collect()`** on a full result set, since `collect()` pulls *every* row back to the Driver's memory and can crash it on large datasets. `.show()` only materializes and prints a small sample (default 20 rows).

---

## 5. Wide Transformation & Shuffle

```python
dept_avg = (
    df_clean.groupBy("department")
    .agg(F.count("*").alias("headcount"), F.round(F.avg("salary"), 2).alias("avg_salary"))
    .orderBy(F.col("avg_salary").desc())
)
```

**Actual result:**
```
+-----------+---------+----------+
| department|headcount|avg_salary|
+-----------+---------+----------+
|    Finance|      304| 113253.34|
|      Sales|      302| 108578.56|
|  Marketing|      334| 108475.43|
|    Support|      325| 108386.66|
|Engineering|      309| 107912.73|
|         HR|      352| 104437.15|
+-----------+---------+----------+
```

**Physical plan confirms the shuffle (`Exchange`):**
```
Exchange rangepartitioning(avg_salary DESC, 200)      <- shuffle for the ORDER BY
   HashAggregate(final: count, avg per department)
      Exchange hashpartitioning(department, 200)      <- shuffle for the GROUP BY
         HashAggregate(partial: count, avg per department, per partition)
            FileScan csv ...
```

`groupBy` is a **wide transformation**: to compute one department's average, Spark needs *every* row for that department, which may be scattered across many input partitions. It must physically redistribute (`Exchange`) rows by hashing on `department` so all matching rows land in the same partition before the final aggregate runs — this network/disk shuffle is the most expensive part of the job and creates a stage boundary in the DAG.

---

## 6. CSV vs. Parquet — Size & Read/Filter Performance

```python
df_clean.write.mode("overwrite").parquet("employees_parquet")
df_clean.write.mode("overwrite").option("header", True).csv("employees_csv_out")
```

**Actual file sizes for the same ~1,926 rows:**
```
Parquet output size: 64K   employees_parquet
CSV output size:     188K  employees_csv_out
```

Parquet is **~3x smaller** here thanks to columnar storage + compression (Snappy) + efficient binary encoding of numeric/date types (vs. CSV's verbose plain-text repetition).

### Predicate Pushdown: `department == 'Engineering'`

```python
csv_filtered = spark.read.csv("employees_csv_out", header=True, inferSchema=True) \
    .filter(F.col("department") == "Engineering").select("employee_id", "salary")

parquet_filtered = spark.read.parquet("employees_parquet") \
    .filter(F.col("department") == "Engineering").select("employee_id", "salary")
```

**Actual timing (309 matching rows both ways — correctness confirmed):**
```
CSV read+filter:     309 rows in 1.2664s
Parquet read+filter: 309 rows in 1.1572s
```

**Physical plans:**
```
Parquet: FileScan parquet [employee_id, department, salary]
         PushedFilters: [IsNotNull(department), EqualTo(department, Engineering)]

CSV:     FileScan csv [employee_id, department, salary]
         PushedFilters: [IsNotNull(department), EqualTo(department, Engineering)]
```

Both plans *list* the same pushed filters, but they don't get the same benefit from them:
- **Parquet** is columnar and stores **min/max statistics per row-group**. Spark can use those stats to **skip entire row-groups** without decompressing/reading them, and reads only the 3 selected columns off disk — the filter and column pruning both translate into real I/O savings.
- **CSV** is row-oriented, uncompressed-per-column, plain text with no stored statistics. Spark still has to **read and parse every row** to evaluate the filter; "pushdown" here only means the filter is applied as early as possible in the plan, not that any data was skipped at the storage layer.

At this small scale (2,000 rows) the timing difference is modest, but the gap **widens dramatically at real-world scale** (millions/billions of rows) since Parquet's row-group skipping avoids I/O that CSV can never avoid.

---

## 7. Full Pipeline: Read → Transform → Filter → Write

```python
final_output = (
    spark.read.csv("employees.csv", header=True, schema=schema)              # READ
    .withColumnRenamed("emp_id", "employee_id")                              # TRANSFORM (rename)
    .withColumn("join_date", F.to_date(F.col("join_date"), "yyyy-MM-dd"))    # TRANSFORM (cast)
    .na.drop(subset=["email"])                                                # CLEAN
    .na.fill({"age": 0, "status": "Unknown"})                                 # CLEAN
    .filter((F.col("status") == "Active") & (F.col("salary") > 60000))       # FILTER
    .select("employee_id", "name", "department", "country", "age", "salary", "join_date", "status")
)
final_output.write.mode("overwrite").parquet("final_pipeline_output")
```

**Actual output:**
```
Final pipeline output row count: 398
+-----------+-----------+-----------+-------+---+---------+----------+------+
|employee_id|       name| department|country|age|   salary| join_date|status|
+-----------+-----------+-----------+-------+---+---------+----------+------+
|     E10001| Employee_1|Engineering|     UK| 36| 96555.28|2018-11-21|Active|
|     E10015|Employee_15|Engineering|    USA| 55| 87723.44|2016-04-20|Active|
|     E10017|Employee_17|      Sales|    USA| 37|135348.23|2018-09-12|Active|
|     E10023|Employee_23|    Support|  India| 32|127197.12|2021-08-13|Active|
|     E10035|Employee_35|         HR|Germany| 43|139711.87|2020-09-15|Active|
+-----------+-----------+-----------+-------+---+---------+----------+------+
Written to: final_pipeline_output/ (Parquet)
```

Because the entire chain is lazy, Spark plans the read, renames, casts, null-handling, and filter as **one optimized DAG** and executes it in a single job when `.write()` (the action) is called — column pruning and filter pushdown apply across the whole pipeline, not just the final step.

---

## Key Insights

1. **Driver / Cluster Manager / Executors** map cleanly onto real execution even in `local[*]` mode — the Driver builds the plan and schedules tasks; a real cluster just separates these roles onto different machines/processes.
2. **Lazy evaluation is the foundation of Spark's optimizer.** Because transformations only build a plan, Catalyst can see the *whole* pipeline and push filters/column selection down into the scan — visible directly in `explain()` output (`PushedFilters`, pruned `ReadSchema`).
3. **Immutability drives the chained-transformation coding style** seen throughout — `withColumn`, `withColumnRenamed`, `filter`, `na.fill` all return new DataFrames.
4. **`groupBy` is a wide transformation.** The physical plan showed two `Exchange` (shuffle) steps — one for the `GROUP BY`, one for the `ORDER BY` — confirming that both require redistributing data across partitions by key.
5. **Parquet beats CSV on both size and pushdown-enabled performance.** In this run, Parquet was ~3x smaller (64K vs 188K) and both formats returned identical correct results (309 rows) — but only Parquet's columnar row-group statistics let Spark actually *skip* I/O, a gap that grows with data volume.
6. **Explicit schemas + column pruning + predicate pushdown** are the concrete techniques that make Spark efficient at scale — all three showed up directly in the `explain()` plans generated by this pipeline.
7. **Best practice confirmed in code:** `.show()` was used throughout for inspection instead of `.collect()`, which avoids pulling full result sets back to the Driver — critical for datasets that don't fit in Driver memory.
