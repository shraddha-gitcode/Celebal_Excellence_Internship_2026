/**
 * Spark Architecture & Efficient Data Processing — Full Pipeline (Scala)
 * Equivalent to spark_architecture_pipeline.py
 *
 * Demonstrates: architecture (Driver/Cluster Manager/Executors), lazy evaluation/DAG,
 * schema handling, filtering, column transforms, wide transformations/shuffle,
 * predicate pushdown, CSV vs Parquet performance, and a read -> transform -> filter -> write pipeline.
 *
 * Run with: spark-submit --class SparkArchitecturePipeline spark_architecture_pipeline.jar
 * or in spark-shell: :load spark_architecture_pipeline.scala
 */

import org.apache.spark.sql.{SparkSession, DataFrame}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

object SparkArchitecturePipeline {

  def main(args: Array[String]): Unit = {

    val spark = SparkSession.builder()
      .appName("Spark-Architecture-Pipeline")
      .master("local[*]")   // execution mode: local, all cores -> Driver + Executors in one JVM
      .getOrCreate()

    import spark.implicits._
    spark.sparkContext.setLogLevel("ERROR")

    println("=" * 80)
    println("SPARK ARCHITECTURE INFO (Driver / Cluster Manager / Executors)")
    println("=" * 80)
    val sc = spark.sparkContext
    println(s"Master (cluster manager URL): ${sc.master}")
    println(s"Application ID (Driver-assigned): ${sc.applicationId}")
    println(s"Default parallelism (executor cores available): ${sc.defaultParallelism}")
    // In local[*] mode, Driver and Executor(s) share one JVM.
    // In cluster mode (YARN/Kubernetes/Standalone) the Driver builds the DAG and
    // negotiates resources from the Cluster Manager, which launches separate
    // Executor JVMs on worker nodes to run tasks.

    println("=" * 80)
    println("STEP 1: READ CSV WITH EXPLICIT SCHEMA (avoid inferSchema on large files)")
    println("=" * 80)

    val schema = StructType(Array(
      StructField("emp_id", StringType, nullable = true),
      StructField("name", StringType, nullable = true),
      StructField("department", StringType, nullable = true),
      StructField("country", StringType, nullable = true),
      StructField("age", IntegerType, nullable = true),
      StructField("salary", DoubleType, nullable = true),
      StructField("join_date", StringType, nullable = true),
      StructField("status", StringType, nullable = true),
      StructField("email", StringType, nullable = true)
    ))

    val dfCsv: DataFrame = spark.read.schema(schema).option("header", "true").csv("employees.csv")
    println(s"Row count (CSV read): ${dfCsv.count()}")
    dfCsv.printSchema()

    println("=" * 80)
    println("STEP 2: LAZY EVALUATION DEMONSTRATION")
    println("=" * 80)

    val t0Build = System.nanoTime()
    val lazyChain = dfCsv
      .filter(col("salary").isNotNull)
      .withColumn("bonus", col("salary") * 0.1)
      .select("emp_id", "department", "salary", "bonus")
    val buildTime = (System.nanoTime() - t0Build) / 1e9
    println(f"Time to BUILD the transformation chain (no action yet): $buildTime%.4fs")

    val t0Exec = System.nanoTime()
    val resultCount = lazyChain.count()   // ACTION -> triggers execution
    val execTime = (System.nanoTime() - t0Exec) / 1e9
    println(f"Time to EXECUTE via .count() action: $execTime%.4fs -> $resultCount rows")
    println("Illustrates lazy evaluation: transformations only build a DAG/lineage graph; " +
      "Spark computes it only when an action runs.")

    println("\nLogical + physical plan (lineage) for the chain above:")
    lazyChain.explain(extended = true)

    println("=" * 80)
    println("STEP 3: SCHEMA MODIFICATION - rename, cast, add column")
    println("=" * 80)

    val dfTransformed = dfCsv
      .withColumnRenamed("emp_id", "employee_id")
      .withColumn("join_date", to_date(col("join_date"), "yyyy-MM-dd"))
      .withColumn("salary_band",
        when(col("salary") >= 100000, "High")
          .when(col("salary") >= 60000, "Mid")
          .otherwise("Low")
      )

    dfTransformed.printSchema()
    dfTransformed.select("employee_id", "join_date", "salary", "salary_band").show(5)

    println("=" * 80)
    println("STEP 4: NULL HANDLING + EFFICIENT FILTERING")
    println("=" * 80)

    val beforeCount = dfTransformed.count()
    val dfClean = dfTransformed
      .na.drop(Seq("email"))                              // drop rows with no email
      .na.fill(Map("age" -> 0, "status" -> "Unknown"))     // fill where recoverable

    println(s"Rows before null handling: $beforeCount | after: ${dfClean.count()}")

    val dfFiltered = dfClean
      .filter(
        col("status") === "Active" &&
        col("salary") > 60000 &&
        col("country").isin("USA", "India", "Germany")
      )
      .select("employee_id", "name", "department", "country", "salary", "salary_band")

    println(s"Filtered result count: ${dfFiltered.count()}")
    dfFiltered.show(5)  // best practice: .show() for inspection, NEVER collect() on full data

    println("=" * 80)
    println("STEP 5: WIDE TRANSFORMATION / SHUFFLE - avg salary by department")
    println("=" * 80)

    val deptAvg = dfClean.groupBy("department")
      .agg(
        count("*").alias("headcount"),
        round(avg("salary"), 2).alias("avg_salary")
      )
      .orderBy(col("avg_salary").desc)

    deptAvg.show()
    println("groupBy triggers a shuffle (Exchange) -> confirmed via explain():")
    deptAvg.explain()

    println("=" * 80)
    println("STEP 6: WRITE TO PARQUET AND CSV, THEN COMPARE")
    println("=" * 80)

    dfClean.write.mode("overwrite").parquet("employees_parquet")
    dfClean.write.mode("overwrite").option("header", "true").csv("employees_csv_out")
    // (compare directory sizes with `du -sh` at the shell level)

    println("=" * 80)
    println("STEP 7: PREDICATE PUSHDOWN - CSV vs PARQUET read+filter timing")
    println("=" * 80)

    val t0Csv = System.nanoTime()
    val dfFromCsv = spark.read.option("header", "true").option("inferSchema", "true")
      .csv("employees_csv_out")
    val csvFiltered = dfFromCsv.filter(col("department") === "Engineering")
      .select("employee_id", "salary")
    val csvCount = csvFiltered.count()
    val csvTime = (System.nanoTime() - t0Csv) / 1e9

    val t0Parquet = System.nanoTime()
    val dfFromParquet = spark.read.parquet("employees_parquet")
    val parquetFiltered = dfFromParquet.filter(col("department") === "Engineering")
      .select("employee_id", "salary")
    val parquetCount = parquetFiltered.count()
    val parquetTime = (System.nanoTime() - t0Parquet) / 1e9

    println(f"CSV read+filter:     $csvCount%d rows in $csvTime%.4fs")
    println(f"Parquet read+filter: $parquetCount%d rows in $parquetTime%.4fs")

    println("\nParquet physical plan (look for PushedFilters in the scan node):")
    parquetFiltered.explain()
    println("\nCSV physical plan:")
    csvFiltered.explain()

    println("=" * 80)
    println("STEP 8: FULL PIPELINE - read -> transform -> filter -> write (Parquet)")
    println("=" * 80)

    val finalOutput = spark.read.schema(schema).option("header", "true").csv("employees.csv")  // READ
      .withColumnRenamed("emp_id", "employee_id")                                              // TRANSFORM
      .withColumn("join_date", to_date(col("join_date"), "yyyy-MM-dd"))                        // TRANSFORM
      .na.drop(Seq("email"))                                                                    // CLEAN
      .na.fill(Map("age" -> 0, "status" -> "Unknown"))                                          // CLEAN
      .filter(col("status") === "Active" && col("salary") > 60000)                             // FILTER
      .select("employee_id", "name", "department", "country", "age", "salary", "join_date", "status")

    finalOutput.write.mode("overwrite").parquet("final_pipeline_output")
    println(s"Final pipeline output row count: ${finalOutput.count()}")
    finalOutput.show(5)
    println("Written to: final_pipeline_output/ (Parquet)")

    println("=" * 80)
    println("DONE")
    println("=" * 80)

    spark.stop()
  }
}
