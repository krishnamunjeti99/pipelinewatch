"""
AWS Glue 5.0 entry point for the Bronze -> Silver transformation.

This is the Glue wrapper around the same transformation logic developed and
tested locally in bronze_to_silver.py. It runs on Glue's managed Spark
(Glue 5.0 = Spark 3.5.4, Python 3.11).

Only the SparkSession setup (via GlueContext) and job bookmarking boilerplate
differ from the local version. The transform() logic is identical.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
)

# Read job parameters passed in via Glue's default_arguments.
# getResolvedOptions strips the leading "--" from each name.
args = getResolvedOptions(sys.argv, ["JOB_NAME", "bronze_path", "silver_path"])

# Glue / Spark setup. GlueContext wraps a SparkContext and gives us a
# configured SparkSession plus Glue-specific features (bookmarks, metrics).
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Explicit schema — identical to the local job. No inference.
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


def transform(df):
    """Identical cleaning/enrichment logic to the local job."""
    return (
        df
        .withColumn("event_ts", F.to_timestamp("timestamp"))
        .withColumn("event_date", F.to_date("event_ts"))
        .withColumn("event_hour", F.hour("event_ts"))
        .withColumn("is_error", F.col("status_code") >= 400)
        .withColumn("is_server_error", F.col("status_code") >= 500)
        .filter(F.col("event_id").isNotNull())
        .filter(F.col("event_ts").isNotNull())
        .filter(F.col("service").isNotNull())
        .dropDuplicates(["event_id"])
    )


# Read Bronze JSON recursively across the partitioned folder structure.
raw = (
    spark.read
    .schema(BRONZE_SCHEMA)
    .option("recursiveFileLookup", "true")
    .json(args["bronze_path"])
)
print(f"Read {raw.count()} raw events from {args['bronze_path']}")

cleaned = transform(raw)
out_count = cleaned.count()
print(f"Writing {out_count} cleaned events to {args['silver_path']}")

# Write partitioned Parquet to Silver. overwrite mode replaces the whole
# silver/ prefix, so re-running fully refreshes the tier (idempotent).
(
    cleaned.write
    .mode("overwrite")
    .partitionBy("event_date", "service")
    .parquet(args["silver_path"])
)

print("Done.")
job.commit()