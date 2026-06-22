"""
Bronze -> Silver transformation for PipelineWatch.

Reads raw JSON Lines event data from the Bronze tier, cleans and types it,
deduplicates, derives useful columns, and writes partitioned Parquet to Silver.

This is written as pure PySpark (DataFrame API) so it runs identically both
locally (for development) and on AWS Glue (for production). The Glue wrapper
is added in a later step.
"""
import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
)


# Explicit schema — we do NOT let Spark infer it.
# Inferring schema requires a full scan of the data and can guess types
# wrong (e.g. reading status_code as a string). Declaring it explicitly is
# faster, deterministic, and catches malformed data.
BRONZE_SCHEMA = StructType([
    StructField("event_id", StringType(), False),
    StructField("timestamp", StringType(), True),
    StructField("service", StringType(), True),
    StructField("endpoint", StringType(), True),
    StructField("method", StringType(), True),
    StructField("status_code", IntegerType(), True),
    StructField("latency_ms", IntegerType(), True),
    StructField("user_id", StringType(), True),
    StructField("region", StringType(), True),
    StructField("ip", StringType(), True),
    StructField("error_message", StringType(), True),
])


def build_spark(app_name: str = "bronze_to_silver") -> SparkSession:
    """Create a SparkSession. Locally this runs a single-node Spark."""
    return (
        SparkSession.builder
        .appName(app_name)
        # Parquet output: use snappy compression (fast, good ratio)
        .config("spark.sql.parquet.compression.codec", "snappy")
        .getOrCreate()
    )


def transform(df):
    """Apply Bronze -> Silver cleaning and enrichment.

    Takes a raw DataFrame, returns the cleaned/enriched DataFrame.
    Separated from IO so it can be unit-tested independently.
    """
    return (
        df
        # Parse the ISO string timestamp into a real timestamp type
        .withColumn("event_ts", F.to_timestamp("timestamp"))
        # Derive a date column for partitioning (one partition per day)
        .withColumn("event_date", F.to_date("event_ts"))
        # Derive an hour column for finer-grained analysis
        .withColumn("event_hour", F.hour("event_ts"))
        # Boolean flag: was this an error response?
        .withColumn("is_error", F.col("status_code") >= 400)
        # Boolean flag: server-side error specifically?
        .withColumn("is_server_error", F.col("status_code") >= 500)
        # Drop rows missing critical fields (data quality gate)
        .filter(F.col("event_id").isNotNull())
        .filter(F.col("event_ts").isNotNull())
        .filter(F.col("service").isNotNull())
        # Deduplicate on event_id — idempotency: re-running must not
        # create duplicate rows
        .dropDuplicates(["event_id"])
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Bronze input path (local or s3://)")
    parser.add_argument("--output", required=True, help="Silver output path (local or s3://)")
    args = parser.parse_args()

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")  # quiet down Spark's verbose logs

    # Read all JSONL files recursively under the input path.
    # recursiveFileLookup lets Spark walk the partitioned folder structure.
    raw = (
        spark.read
        .schema(BRONZE_SCHEMA)
        .option("recursiveFileLookup", "true")
        .json(args.input)
    )

    print(f"Read {raw.count()} raw events from {args.input}")

    cleaned = transform(raw)

    out_count = cleaned.count()
    print(f"Writing {out_count} cleaned events to {args.output}")

    # Write partitioned Parquet. Partitioning by event_date and service
    # mirrors our query patterns and enables partition pruning.
    (
        cleaned.write
        .mode("overwrite")
        .partitionBy("event_date", "service")
        .parquet(args.output)
    )

    print("Done.")
    spark.stop()


if __name__ == "__main__":
    main()