# Spark Architecture & Efficient Data Processing — Deliverable Bundle

## Contents

| File | Description |
|---|---|
| `spark_architecture_pipeline.py` | Full runnable **PySpark** pipeline: architecture info, lazy evaluation/DAG demo, schema handling, filtering, wide transformations/shuffle, CSV vs Parquet, predicate pushdown, full read→transform→filter→write pipeline. |
| `spark_architecture_pipeline.scala` | Equivalent **Scala** version of the same pipeline (Spark SQL API), runnable via `spark-shell` or `spark-submit`. |
| `Spark_Architecture_Pipeline_Report.md` | Narrative write-up combining the code, **actual execution results**, and insights on performance/architecture. |
| `execution_results_pyspark.txt` | Raw console output from actually running the PySpark script. |
| `execution_results_scala.txt` | Raw console output from actually running the Scala script (via spark-shell). |
| `sample_input_employees.csv` | The synthetic 2,000-row input dataset used by both scripts (has intentional nulls to demonstrate cleaning). |

## How to run

**PySpark:**
```bash
pip install pyspark
python3 spark_architecture_pipeline.py
```

**Scala (via spark-shell):**
```bash
spark-shell --master local[*]
scala> :load spark_architecture_pipeline.scala
scala> SparkArchitecturePipeline.main(Array())
```

Both scripts expect `employees.csv` (rename `sample_input_employees.csv` to `employees.csv`, or edit the path in the script) in the working directory, and will write output folders (`employees_parquet/`, `employees_csv_out/`, `final_pipeline_output/`) alongside it.

## Quick summary of what was verified by actually running the code

- **Architecture**: Driver/Cluster Manager/Executor roles confirmed via live `SparkContext` info (`local[*]`, application ID, parallelism).
- **Lazy evaluation**: chain-building took ~0.17s (no execution) vs. ~0.8s for the actual `.count()` action — confirmed via `explain(extended)` showing Catalyst's optimized/physical plan.
- **Schema modification**: `emp_id` → `employee_id` rename, `join_date` string → `DateType` cast, new `salary_band` derived column — all confirmed in `printSchema()` output.
- **Null handling & filtering**: 2000 → 1926 rows after email-null drop + fill; 192 rows after business filter (Active, salary > 60000, specific countries).
- **Wide transformation/shuffle**: `groupBy("department")` physical plan shows real `Exchange` (hash + range partitioning) operators.
- **CSV vs Parquet**: Parquet output was **64K vs. CSV's 188K** for the same ~1,926 rows; predicate pushdown (`department = 'Engineering'`) verified via `explain()` on both formats, with identical correct result (309 rows) but only Parquet able to skip I/O via row-group statistics.
- **Full pipeline**: read → rename/cast → clean nulls → filter → write to Parquet, producing 398 final rows, following the show()-not-collect() best practice throughout.
