"""
PipelineWatch full pipeline.

Orchestrates the entire platform end to end:
    generate logs -> Glue (Bronze->Silver) -> crawler -> dbt build (Gold)

Includes per-task retries and a failure callback for alerting.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow.sdk import dag, task
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
from airflow.providers.standard.operators.bash import BashOperator

GLUE_JOB_NAME = "pipelinewatch-bronze-to-silver-dev"
CRAWLER_NAME = "pipelinewatch-silver-crawler-dev"

DBT_DIR = "/usr/local/airflow/include/dbt"
DBT_BIN = "/usr/local/airflow/dbt_venv/bin/dbt"


def alert_on_failure(context):
    """Fires when any task fails. In production this would post to Slack
    or send email; here it logs a clear, structured alert."""
    ti = context["task_instance"]
    print(
        "PIPELINE ALERT — task failed:\n"
        f"  dag:   {ti.dag_id}\n"
        f"  task:  {ti.task_id}\n"
        f"  run:   {context['run_id']}\n"
        f"  tries: {ti.try_number}\n"
        "  (In prod: route this to Slack/email/PagerDuty.)"
    )


default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": alert_on_failure,
}


@dag(
    # Production: schedule="@daily". Kept None in dev to control Glue/crawler cost
    # (each run ~$0.20). Flip to a cron/preset to enable automated runs.
    schedule=None,
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

    run_glue = GlueJobOperator(
        task_id="run_glue_job",
        job_name=GLUE_JOB_NAME,
        wait_for_completion=True,
    )

    run_crawler = GlueCrawlerOperator(
        task_id="run_crawler",
        config={"Name": CRAWLER_NAME},
        wait_for_completion=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"DBT_PROFILES_DIR={DBT_DIR} "
            f"{DBT_BIN} build "
            f"--project-dir {DBT_DIR} "
            f"--log-path /tmp/dbt_logs "
            f"--target-path /tmp/dbt_target"
        ),
    )

    generate_logs() >> run_glue >> run_crawler >> dbt_build


pipelinewatch_pipeline()
