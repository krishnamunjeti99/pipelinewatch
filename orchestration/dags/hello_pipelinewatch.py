"""
First PipelineWatch DAG — confirms Airflow is working and can reach AWS.
Uses the Airflow 3 TaskFlow API (decorators from airflow.sdk).
"""
from datetime import datetime

from airflow.sdk import dag, task


@dag(
    schedule=None,                  # manual trigger only, for now
    start_date=datetime(2026, 1, 1),
    catchup=False,                  # don't backfill past dates
    tags=["pipelinewatch", "test"],
)
def hello_pipelinewatch():

    @task
    def say_hello() -> str:
        print("Hello from Airflow — PipelineWatch orchestration is alive!")
        return "hello"

    @task
    def check_aws() -> str:
        import boto3
        ident = boto3.client("sts").get_caller_identity()
        print(f"Connected to AWS account {ident['Account']} as {ident['Arn']}")
        return ident["Account"]

    @task
    def summarize(greeting: str, account: str) -> None:
        print(f"Greeting='{greeting}', AWS account={account}. Day 2 works.")

    # Dependencies are expressed by passing outputs as inputs:
    # summarize runs only after say_hello AND check_aws succeed.
    g = say_hello()
    a = check_aws()
    summarize(g, a)


hello_pipelinewatch()
