"""
PipelineWatch core pipeline.

Orchestrates the AWS-native pipeline end to end:
    generate fresh logs -> Bronze->Silver Glue job -> Silver crawler

The dbt Gold build is added as a fourth task in the next iteration.
Uses the Airflow 3 TaskFlow API plus the Amazon provider's Glue operators.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow.sdk import dag, task
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator

GLUE_JOB_NAME = "pipelinewatch-bronze-to-silver-dev"
CRAWLER_NAME = "pipelinewatch-silver-crawler-dev"

# default_args apply to every task in the DAG.
# retries + retry_delay make the pipeline resilient to transient failures.
default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    schedule=None,                 # manual trigger (keeps Glue costs controlled)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["pipelinewatch", "pipeline"],
)
def pipelinewatch_pipeline():

    @task
    def generate_logs() -> int:
        """Generate one hour of fresh synthetic events into the Bronze tier."""
        sys.path.insert(0, "/usr/local/airflow/include")
        from generate_logs import run

        bucket = os.environ["BRONZE_BUCKET"]
        events_per_hour = 2000
        run(bucket, events_per_hour=events_per_hour)
        return events_per_hour

    # Trigger the existing Glue job and block until it finishes.
    run_glue = GlueJobOperator(
        task_id="run_glue_job",
        job_name=GLUE_JOB_NAME,
        wait_for_completion=True,
    )

    # Run the crawler to register any new Silver partitions, block until done.
    run_crawler = GlueCrawlerOperator(
        task_id="run_crawler",
        config={"Name": CRAWLER_NAME},
        wait_for_completion=True,
    )

    # Dependency chain: generate -> transform -> catalog
    generate_logs() >> run_glue >> run_crawler


pipelinewatch_pipeline()
