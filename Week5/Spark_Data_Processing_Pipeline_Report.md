# Spark Fundamentals — Data Cleaning, Transformation & Aggregation Pipeline

A full, runnable PySpark pipeline executed against a synthetic, intentionally messy
sales dataset (530 rows, with injected duplicates, nulls, and empty strings) to
demonstrate every stage of a real Spark data-processing workflow.

**Files:**
- `spark_pipeline.py` — the complete runnable script
- This report — narrative walkthrough + actual output from running the script

---

## 1. Why Spark instead of MapReduce

| MapReduce | Spark |
|---|---|
| Writes intermediate results to disk between every Map/Reduce stage | Keeps data **in memory** across stages and iterations |
| Each iteration of an algorithm = a new job re-reading from disk | Data can be **cached once** (`.cache()`) and reused across iterations |
| Rigid two-stage model, high job-startup latency | Flexible **DAG** of stages, optimized as a whole (Catalyst optimizer) |
| Low-level API (map/reduce only) | High-level DataFrame/SQL API with built-in optimization |

This is why Spark is typically **10–100x faster**, especially for iterative ML and interactive queries — RAM access beats repeated disk I/O.

---

## 2. Dataset & Setup

The demo dataset (`raw_sales.csv`) simulates a sales system with realistic messiness:

```
user_id,transaction_date,store_id,city,region,product_category,age,subscription,sale_amount,status,raw_timestamp,email,username
U1230,2024-06-22,S1004,Atlanta,South,Electronics,33,Basic,205.28,Completed,2024-10-23 18:52:00,user1230@example.com,user_1230
U1428,2024-08-03,S1003,San Francisco,West,Apparel,45,Basic,184.47,,2024-10-17 10:11:00,user1428@example.com,
U1478,2024-12-13,S1019,Dallas,South,Grocery,67,Free,338.53,,2024-05-03 04:08:00,,user_1478
...
```

It contains: **30 injected duplicate transactions**, missing `age`/`sale_amount`/`status`/`email` values, and empty `username` strings — exactly the kind of mess a real pipeline has to handle.

An **explicit schema** (`StructType`) is used instead of `inferSchema=True`, avoiding the risk of Spark silently mis-parsing inconsistent date/number formats (see §7).

```python
spark = SparkSession.builder.appName("Week5-Spark-Fundamentals").master("local[*]").getOrCreate()

df_raw = spark.read.csv("raw_sales.csv", header=True, schema=schema)
```

**Result:** `Raw row count: 530`

---

## 3. Data Cleaning

### 3a. Remove duplicates (keyed on `user_id` + `transaction_date`)

```python
df_dedup = df_raw.dropDuplicates(["user_id", "transaction_date"])
```
**Result:** `500 rows remain (removed 30 duplicate rows)` ✅ exactly matches the 30 duplicates injected.

### 3b. Handle nulls

```python
median_age = df_dedup.approxQuantile("age", [0.5], 0.01)[0]
df_filled = df_dedup.na.fill({
    "sale_amount": 0.0,
    "status": "Unknown",
    "age": int(median_age),
})
```
**Result:** `Median age used to fill null ages: 43`

- `sale_amount` → filled with `0.0` (a missing amount shouldn't vanish from revenue totals)
- `status` → filled with `"Unknown"` (preserves the row, flags it explicitly)
- `age` → filled with the **median** (robust to outliers, unlike mean)

### 3c. Remove rows with unusable identity fields

```python
df_clean = df_filled.filter(
    F.col("email").isNotNull() & (F.trim(F.col("username")) != "")
)
```
**Result:** `449 rows remain (removed 51 rows with null email or empty username)`

---

## 4. Schema Modification — Casting & Renaming

```python
df_clean = (
    df_clean
    .withColumn("event_time", F.to_timestamp(F.col("raw_timestamp"), "yyyy-MM-dd HH:mm:ss"))
    .drop("raw_timestamp")
    .withColumnRenamed("sale_amount", "revenue")
)
```

**Resulting schema:**
```
root
 |-- user_id: string
 |-- transaction_date: string
 |-- store_id: string
 |-- city: string
 |-- region: string
 |-- product_category: string
 |-- age: integer
 |-- subscription: string
 |-- revenue: double            <- renamed from sale_amount
 |-- status: string
 |-- email: string
 |-- username: string
 |-- event_time: timestamp      <- cast from raw_timestamp (string)
```

**Sample rows (`event_time`, `revenue`):**
```
+-------------------+-------+
|event_time         |revenue|
+-------------------+-------+
|2024-01-01 02:13:00|274.96 |
|2024-12-14 10:17:00|8.22   |
|2024-07-03 17:18:00|366.22 |
|2024-07-09 14:40:00|428.38 |
|2024-05-21 22:35:00|85.88  |
+-------------------+-------+
```

Note: `df.withColumn()` / `.drop()` / `.withColumnRenamed()` each return a **new DataFrame** — Spark DataFrames are **immutable**, so cleaning steps must be chained/reassigned rather than mutated in place.

---

## 5. Filtering

### Age range + subscription tier
```python
df_young_premium = df_clean.filter(
    F.col("age").between(18, 30) & (F.col("subscription") == "Premium")
)
```
**Result (sample):**
```
+-------+---+------------+------+
|user_id|age|subscription|region|
+-------+---+------------+------+
|  U1029| 24|     Premium| North|
|  U1037| 30|     Premium|  West|
|  U1066| 19|     Premium| South|
|  U1085| 25|     Premium|  West|
|  U1089| 26|     Premium|  East|
+-------+---+------------+------+
```

### Region filter
```python
df_west = df_clean.filter(F.col("region") == "West")
```

---

## 6. Aggregation — West region, average revenue by category

```python
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
```

**Actual result:**
```
+----------------+----------------+-----------+-------------+-----------+-----------+
|product_category|num_transactions|avg_revenue|total_revenue|min_revenue|max_revenue|
+----------------+----------------+-----------+-------------+-----------+-----------+
|Home & Kitchen  |20              |282.97     |5659.3       |52.68      |470.26     |
|Electronics     |24              |246.96     |5927.13      |0.0        |489.07     |
|Apparel         |23              |234.55     |5394.73      |0.0        |449.48     |
|Toys            |19              |219.25     |4165.82      |0.0        |480.59     |
|Grocery         |25              |198.76     |4968.96      |0.0        |497.65     |
+----------------+----------------+-----------+-------------+-----------+-----------+
```

The `0.0` minimums are the null-filled rows from §3b surfacing correctly — the fill decision made these **visible and intentional** instead of hidden nulls.

---

## 7. GroupBy + Condition on Aggregated Result (HAVING-style)

```python
city_counts = (
    df_clean.groupBy("city")
    .count()
    .filter(F.col("count") > 15)
    .orderBy(F.col("count").desc())
)
```

**Actual result** (all 12 cities passed the >15 threshold in this dataset):
```
+-------------+-----+
|city         |count|
+-------------+-----+
|Atlanta      |48   |
|Chicago      |46   |
|Miami        |42   |
|Dallas       |41   |
|Los Angeles  |40   |
|Seattle      |40   |
|Minneapolis  |37   |
|Detroit      |36   |
|New York     |35   |
|San Francisco|31   |
|Houston      |27   |
|Boston       |26   |
+-------------+-----+
```

`.filter()` applied **after** `groupBy().count()` filters the aggregated result — equivalent to SQL's `HAVING`, not `WHERE`.

---

## 8. Wide Transformations & Shuffle

```python
grouped = df_clean.groupBy("region").agg(F.sum("revenue").alias("total_revenue"))
grouped.explain(mode="formatted")
```

The physical plan confirms an **`Exchange`** step (Spark's shuffle operator) sitting between a *partial* hash aggregation and the *final* hash aggregation:

```
HashAggregate (partial_sum, per-partition)
   -> Exchange  hashpartitioning(region, 200)   <-- SHUFFLE: rows redistributed by key
      -> HashAggregate (final sum, per-region)
```

**Why this matters:** `groupBy` is a **wide transformation** — computing a single region's total requires rows for that region from *every* input partition. Spark must physically move data across the cluster (write, transfer over network, read) so all rows sharing a key land in the same partition before the final aggregation can run. This shuffle/`Exchange` step is the most expensive part of a Spark job and marks a **stage boundary** in the DAG — the next stage can't start reading until the current stage finishes writing shuffle output.

(In this small local demo, Adaptive Query Execution coalesced the shuffle down to a single output partition — but the `Exchange` step itself still occurred, which is what defines the wide transformation.)

---

## 9. Full End-to-End Pipeline

**Requirement:** dedupe → fill null prices with 0 → group by `store_id` → total revenue.

```python
final_pipeline_result = (
    df_raw
    .dropDuplicates(["user_id", "transaction_date"])                 # 1. remove duplicates
    .na.fill({"sale_amount": 0.0})                                   # 2. fill null prices with 0
    .groupBy("store_id")
    .agg(F.round(F.sum("sale_amount"), 2).alias("total_revenue"))    # 3. total revenue per store
    .orderBy(F.col("total_revenue").desc())
)
```

**Actual result (top 10 stores by revenue):**
```
+--------+-------------+
|store_id|total_revenue|
+--------+-------------+
|S1010   |7929.36      |
|S1001   |7455.18      |
|S1004   |7361.41      |
|S1009   |7277.06      |
|S1020   |7062.64      |
|S1015   |6915.64      |
|S1014   |6251.32      |
|S1019   |6221.54      |
|S1002   |5776.9       |
|S1017   |5706.5       |
+--------+-------------+
```

Order matters here: deduplicating **before** aggregating prevents duplicate transactions from inflating store revenue, and filling nulls **before** `sum()` ensures missing sale amounts contribute `0` explicitly rather than distorting the aggregate silently.

---

## Key Insights

1. **In-memory + DAG execution** is what makes Spark faster than MapReduce, especially for iterative/interactive work — this demo's entire 8-step pipeline runs as one optimized job rather than 8 separate disk round-trips.
2. **Immutability shapes the coding style**: every cleaning step (`dropDuplicates`, `na.fill`, `filter`, `withColumn`, `drop`, `withColumnRenamed`) returns a new DataFrame, so pipelines are naturally written as chained transformations.
3. **Clean before you aggregate.** In this run, deduplication removed exactly the 30 injected duplicate rows, and null-filling made "missing revenue" an explicit, visible `0.0` rather than a value quietly excluded from `avg()`'s denominator.
4. **`filter()` after `groupBy()`** behaves like SQL's `HAVING` — filtering the aggregated result, not the raw rows.
5. **`groupBy`/aggregation is a wide transformation.** The `explain()` plan shows a concrete `Exchange` (shuffle) step — this is the operation to watch for cost/performance in real Spark jobs.
6. **Explicit schemas beat `inferSchema=True`** for messy data — this pipeline defined types upfront and used `to_timestamp()` with an explicit format string, avoiding the silent-null risk of mismatched date formats.
7. **Pipeline ordering is a correctness issue, not just a style choice** — deduping and null-handling before aggregation directly changed the final revenue totals compared to aggregating raw, messy data.
