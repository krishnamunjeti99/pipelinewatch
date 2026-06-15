# PipelineWatch

A production-grade telemetry analytics platform built on AWS.

**Architecture:** Medallion data lake (Bronze/Silver/Gold) on S3, with batch + streaming ingestion, Spark transformations, dbt for the warehouse layer, orchestrated by Airflow, served via FastAPI on ECS Fargate.

**Status:** In development. See SYSTEM_DESIGN.md for the design doc.
