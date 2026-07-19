# Week 5 — Spark Fundamentals: Cleaning, Transformation & Aggregation

---

## Q1: Key limitations of MapReduce that make Spark preferable

| Limitation of MapReduce | How Spark addresses it |
|---|---|
| **Disk I/O between every Map and Reduce stage** — intermediate results are written to HDFS disk | Spark keeps intermediate data **in memory (RDD/DataFrame caching)**, avoiding repeated disk writes/reads |
| **Poor support for iterative algorithms** (ML, graph processing) — each iteration is a fresh MapReduce job that re-reads data from disk | Spark can **cache/persist** a dataset once and reuse it across iterations |
| **High latency** — job startup overhead, rigid two-stage (Map → Reduce) model | Spark builds a flexible **DAG (Directed Acyclic Graph)** of stages, so complex pipelines run as one optimized job |
| **Verbose, low-level API** (only map/reduce primitives) | Spark offers **high-level APIs**: DataFrame, Dataset, SQL, MLlib, GraphX, Structured Streaming |
| **No good support for streaming/real-time** | Spark Structured Streaming handles both batch and streaming with the same API |
| **Limited interactive/ad-hoc querying** | Spark SQL + in-memory caching enables fast interactive queries |

**Bottom line:** MapReduce trades speed for fault tolerance by writing to disk at every stage. Spark keeps data in memory across stages/iterations and uses a DAG scheduler, making it typically **10x–100x faster**, especially for iterative and interactive workloads.

---

## Q2: In-memory computing and iterative ML algorithms

Iterative ML algorithms (gradient descent, k-means, PageRank, etc.) touch the **same dataset repeatedly** across many iterations.

- **Disk-based systems (MapReduce):** Each iteration = a separate job. Data is read from disk → processed → written back to disk, then the next iteration re-reads from disk. With hundreds of iterations, disk I/O dominates runtime.
- **Spark:** The dataset is loaded once and **cached in memory** (`.cache()` / `.persist()`) as an RDD/DataFrame. Every subsequent iteration reads directly from RAM instead of disk.

```python
# Example: iterative computation benefiting from in-memory caching
df = spark.read.parquet("s3://data/features.parquet")
df.cache()          # materializes and keeps df in memory after first action
df.count()          # triggers caching

for i in range(iterations):
    # each iteration reuses the cached in-memory DataFrame
    result = df.groupBy("cluster_id").agg(F.avg("value").alias("centroid"))
    result.show()
```

Since RAM access is orders of magnitude faster than disk access, and Spark also avoids re-serializing/re-reading data between stages, iterative workloads see dramatic speedups — this is the core reason Spark MLlib outperforms classic Hadoop MapReduce-based ML.

---

## Q3: Remove duplicate rows based on `user_id` and `transaction_date`

```python
from pyspark.sql import functions as F

df_clean = df.dropDuplicates(["user_id", "transaction_date"])

df_clean.show()
```

- `dropDuplicates(subset)` keeps the **first occurrence** it encounters for each unique combination of the given columns and drops the rest.
- If you use `dropDuplicates()` with no arguments, it considers **all columns**.

---

## Q4: Filter `region == 'West'` then average `sale_amount` by `product_category`

```python
result = (
    df_sales
    .filter(F.col("region") == "West")
    .groupBy("product_category")
    .agg(F.avg("sale_amount").alias("avg_sale_amount"))
)

result.show()
```

**Sample output:**

```
+------------------+------------------+
| product_category | avg_sale_amount  |
+------------------+------------------+
| Electronics       | 245.67          |
| Apparel           | 89.32           |
| Home & Kitchen    | 132.10          |
+------------------+------------------+
```

---

## Q5: `.na.drop()` vs `.na.fill()`

| Method | Behavior |
|---|---|
| `.na.drop()` | **Removes rows** that contain null values (in any column, or specific subset columns you pass) |
| `.na.fill()` | **Replaces** null values with a specified default value, keeping the row |

```python
# .na.drop() – removes rows with any null
df_no_nulls = df.na.drop()

# .na.drop() on specific columns only
df_no_nulls_status = df.na.drop(subset=["status"])

# .na.fill() – fill nulls in the 'status' column with 'Unknown'
df_filled = df.na.fill({"status": "Unknown"})

df_filled.show()
```

Use `drop()` when a null makes the row unusable/incomplete; use `fill()` when you want to preserve the row but need a safe placeholder value (important before aggregations, joins, or ML feature encoding).

---

## Q6: Count of records per city, only where count > 100

```python
result = (
    df.groupBy("city")
    .count()
    .filter(F.col("count") > 100)
)

result.show()
```

> Note: `.filter()` after `groupBy().count()` uses `HAVING`-like semantics — it filters on the **aggregated** result, not the raw rows.

Equivalent Spark SQL:

```sql
SELECT city, COUNT(*) AS count
FROM df
GROUP BY city
HAVING COUNT(*) > 100
```

---

## Q7: Immutability and "data cleaning" operations (drop/rename columns)

Spark DataFrames are **immutable** — no in-place operation exists. Every transformation (`.drop()`, `.withColumnRenamed()`, `.filter()`, etc.) returns a **brand-new DataFrame**; the original is untouched.

Practical implications for data cleaning:

1. **You must reassign the result** to a variable (often the same name) to "keep" the change:
   ```python
   df = df.drop("temp_col")
   df = df.withColumnRenamed("old_name", "new_name")
   ```
2. **Chaining is natural and encouraged** — since each step returns a new DataFrame, cleaning pipelines are typically written as a fluent chain:
   ```python
   df_clean = (
       df.drop("temp_col")
         .withColumnRenamed("cust_nm", "customer_name")
         .na.fill({"status": "Unknown"})
   )
   ```
3. **Lazy evaluation** — none of these transformations actually execute until an action (`.show()`, `.count()`, `.write()`) is called. Spark builds a logical plan and optimizes it (via Catalyst) before execution, so a long chain of "cleaning" steps costs nothing extra at definition time.
4. **Safety/reproducibility** — because the source DataFrame is never mutated, you can always go back to `df` (or re-read the source) if a cleaning step produces unexpected results; there's no risk of silently corrupting original data in memory.

---

## Q8: Filter age between 18–30 (inclusive) AND subscription == 'Premium'

```python
result = df.filter(
    (F.col("age").between(18, 30)) & (F.col("subscription") == "Premium")
)

result.show()
```

`between()` is inclusive on both ends, equivalent to `age >= 18 AND age <= 30`.

---

## Q9: Why handle nulls before aggregations like `sum()`/`avg()`?

- **`sum()` ignores nulls silently**, but if an entire group is null, the sum reports `null` instead of `0`, which can be misread as "no data" rather than "zero value."
- **`avg()` computes the mean only over non-null rows** — nulls are excluded from both the numerator and the denominator. If nulls actually represent zero (e.g., a missing sale, a failed transaction with a real value of 0), leaving them as null will **inflate the average** because the count used is smaller than the true row count.
- **Downstream errors compound**: joins, further math (`col_a / col_b`), and ML feature pipelines can propagate `null` or throw errors if nulls aren't resolved first.
- **Business meaning must be decided explicitly**: null could mean "unknown," "not applicable," or "zero" — each has a different correct treatment (drop, fill with 0, fill with mean/median). Aggregating first hides this decision and bakes in an ambiguous/incorrect assumption.

**Best practice:** decide and apply a null-handling strategy (`.na.fill()` or `.na.drop()`) *before* `.agg()`, so the aggregation reflects an intentional, well-understood dataset.

---

## Q10: Cast `raw_timestamp` to TimestampType and rename to `event_time`

```python
from pyspark.sql.types import TimestampType

df = df.withColumn("event_time", F.col("raw_timestamp").cast(TimestampType())) \
       .drop("raw_timestamp")
```

Alternative in one step using `withColumnRenamed` + cast:

```python
df = (
    df.withColumn("raw_timestamp", F.col("raw_timestamp").cast(TimestampType()))
      .withColumnRenamed("raw_timestamp", "event_time")
)
```

---

## Q11: The "Shuffle" process and why grouping is a wide transformation

**Shuffle** is the process of **redistributing data across partitions/executors** so that all records sharing the same key end up on the same partition/node.

During a `groupBy()`:
1. Spark must ensure every row with `key = X` lands on the **same partition** (regardless of which partition it started in) so it can be aggregated together.
2. This requires **writing data out from each partition, sending it across the network** to the target partition (based on a hash of the key), and **reading it back in** on the receiving side.
3. This involves disk I/O (spill files) and network transfer, making shuffle the **most expensive operation** in Spark.

**Why it's a "wide" transformation:**
- A **narrow transformation** (e.g., `map`, `filter`) only needs data from a **single input partition** to compute a single output partition — no data movement between partitions.
- A **wide transformation** (e.g., `groupBy`, `join`, `distinct`, `repartition`) requires data from **multiple/all input partitions** to compute each output partition — hence data must be shuffled across the cluster.
- Because of this all-to-all dependency, wide transformations create a **stage boundary** in Spark's DAG — Spark cannot pipeline them with the following operation; it must fully complete the shuffle-write of the current stage before the next stage's shuffle-read can begin.

---

## Q12: Remove rows where `email` is null OR `username` is an empty string

```python
df_clean = df.filter(
    F.col("email").isNotNull() & (F.trim(F.col("username")) != "")
)
```

Or equivalently, filtering out the "bad" rows explicitly:

```python
df_clean = df.filter(
    ~(F.col("email").isNull() | (F.trim(F.col("username")) == ""))
)
```

> Using `F.trim()` also catches usernames that are just whitespace (`"   "`), not only exact empty strings.

---

## Q13: Multiple statistics at once with `.agg()`

```python
result = df.agg(
    F.min("price").alias("min_price"),
    F.max("price").alias("max_price"),
    F.mean("price").alias("mean_price")
)

result.show()
```

Combined with `groupBy` (per-group statistics):

```python
result = df.groupBy("category").agg(
    F.min("price").alias("min_price"),
    F.max("price").alias("max_price"),
    F.mean("price").alias("mean_price"),
    F.count("price").alias("num_records")
)

result.show()
```

`.agg()` accepts any number of aggregate expressions in a single pass over the data — Spark computes all of them together in one shuffle/scan rather than requiring separate queries.

---

## Q14: Risk of `inferSchema=true` with messy/inconsistent date formats

`inferSchema=true` makes Spark **sample the data and guess column types automatically**. With inconsistent date formats this is risky because:

1. **Wrong type inference** — if most values look like dates but some are malformed (`"2023-13-45"`, `"N/A"`, `"31/02/2023"`), Spark may fall back to inferring the column as **`StringType`** instead of `DateType`/`TimestampType`, silently disabling date-based operations later.
2. **Silent nulls (`corrupt record` behavior)** — even if a date type is inferred, values that don't match the assumed pattern get **silently converted to `null`** during parsing rather than raising an error, causing **quiet data loss** that's easy to miss.
3. **Inconsistent inference across mixed formats** — e.g., a mix of `MM/dd/yyyy` and `dd/MM/yyyy` in the same column will parse *some* rows incorrectly (day/month swapped) without any error, since both look syntactically valid.
4. **Performance cost** — schema inference requires an **extra pass over the data** (or a sample) before the real read, adding overhead, especially on large files.
5. **Non-reproducibility** — inferred schema can vary between reads if the underlying sample changes (e.g., new data added), leading to schema drift between runs.

**Best practice:** define an explicit schema (`StructType`) with string columns for raw date fields, then parse dates explicitly using `to_date()`/`to_timestamp()` with a specified format string, and inspect unparseable rows rather than letting Spark silently null them out.

```python
df = df.withColumn(
    "event_date",
    F.to_date(F.col("raw_date_str"), "yyyy-MM-dd")  # explicit format
)
# rows that fail to match the format become null and can be audited:
bad_rows = df.filter(F.col("raw_date_str").isNotNull() & F.col("event_date").isNull())
```

---

## Q15: Final processing pipeline

**Requirements:** (1) remove duplicates, (2) fill null prices with 0, (3) group by `store_id` for total revenue.

```python
from pyspark.sql import functions as F

# Assume df has columns: store_id, transaction_id, price, ...

pipeline_result = (
    df
    .dropDuplicates()                          # Step 1: remove duplicate rows
    .na.fill({"price": 0})                     # Step 2: fill null prices with 0
    .groupBy("store_id")
    .agg(F.sum("price").alias("total_revenue")) # Step 3: total revenue per store
    .orderBy(F.col("total_revenue").desc())
)

pipeline_result.show()
```

**Sample output:**

```
+---------+--------------+
| store_id| total_revenue|
+---------+--------------+
| S1042   | 158230.50    |
| S1007   | 142980.75    |
| S1015   | 98450.20     |
+---------+--------------+
```

**Pipeline notes:**
- Steps are chained lazily — nothing executes until `.show()` (an action) triggers the DAG.
- `dropDuplicates()` should run *before* aggregation so duplicate transactions don't inflate revenue.
- `na.fill()` runs before `.agg()` so `sum()` doesn't silently exclude/miscount null-priced rows (see Q9).
- `groupBy().agg()` triggers a shuffle (see Q11) since revenue must be combined across all rows sharing the same `store_id`, regardless of original partition.

---

## Key Insights

- **Spark's edge over MapReduce** comes from in-memory computation and DAG-based execution, which is especially impactful for iterative and interactive workloads.
- **Immutability** shapes Spark's coding style into fluent, chained, reassignment-based pipelines rather than in-place mutation.
- **Order matters in cleaning pipelines**: dedupe → handle nulls → THEN aggregate. Aggregating before cleaning bakes in inaccurate results.
- **groupBy, join, distinct, and repartition are "wide" transformations** — they require a shuffle, which is the main performance cost to be mindful of in Spark jobs.
- **Schema discipline** (explicit schemas, deliberate casting) is safer than `inferSchema=true` for messy real-world data — inference trades correctness for convenience.
