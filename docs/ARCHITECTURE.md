# PipelineWatch — System Design & Architecture

A reference design for the PipelineWatch data platform: the architecture, the
data flow, the key engineering decisions and their trade-offs, and how the
system would be taken to production. This document is written to be read on its
own — by a reviewer, an interviewer, or a future maintainer.

---

## 1. Purpose & scope

PipelineWatch ingests application telemetry, transforms it into clean and
business-ready datasets, and serves analytics on top of it. It is a complete,
production-style **medallion lakehouse** on AWS, built to demonstrate the full
data lifecycle: ingestion, transformation, analytics engineering, orchestration,
and serving.

The data is synthetic so the whole pipeline can run safely and cheaply, but the
tools, patterns, and design trade-offs are the same ones used in production data
platforms.

**Design goals**

- **Correctness & reproducibility** — every stage is idempotent and defined as code.
- **Cost efficiency** — the whole platform runs for cents per month.
- **Separation of concerns** — each tool does one job; tiers have clear contracts.
- **Legibility** — the architecture is simple to reason about and explain.

---

## 2. High-level architecture

PipelineWatch follows the **medallion architecture** — data flows through
progressively refined tiers (Bronze → Silver → Gold), each with a distinct
purpose and data contract.

```
                          ┌──────────────────────────────────────────────┐
                          │            Apache Airflow (DAG)               │
                          │   orchestrates the full pipeline end to end   │
                          │   with dependencies, retries, and alerting    │
                          └──────────────────────────────────────────────┘
                                 │           │           │           │
                                 ▼           ▼           ▼           ▼
   ┌──────────┐   generate   ┌────────┐  ┌────────┐  ┌─────────┐  ┌──────────┐
   │ Synthetic│ ───────────► │ BRONZE │  │ Glue   │  │ Crawler │  │   dbt    │
   │   logs   │   (Python)   │  raw   │─►│PySpark │─►│ catalog │─►│  build   │
   └──────────┘              │  JSON  │  │ job    │  └─────────┘  │  (Gold)  │
                             └────────┘  └────────┘               └──────────┘
                                  │           │                        │
                              S3 (raw)    S3 SILVER                  S3 GOLD
                                          cleaned,                 marts +
                                          partitioned              SCD2 dim
                                          Parquet                     │
                                                                      ▼
                                                          ┌────────────────────┐
                                                          │  FastAPI + Chart.js│
                                                          │ analytics dashboard│
                                                          │ (reads Gold via    │
                                                          │  Athena, cached)   │
                                                          └────────────────────┘

   All infrastructure as code (Terraform) · queryable throughout (Athena) · CI on every push
```

| Tier | Contract | Format | Engine |
|------|----------|--------|--------|
| **Bronze** | Raw, immutable, append-only | JSON, partitioned by service/time | Python → S3 |
| **Silver** | Cleaned, typed, deduplicated, one row per event | Parquet, partitioned | PySpark on AWS Glue |
| **Gold** | Business-ready aggregates & dimensions | Parquet / Iceberg | dbt (Athena) |
| **Serving** | Read-optimized analytics | JSON over HTTP | FastAPI + Athena |

---

## 3. Data flow

1. **Ingestion.** A Python generator emits synthetic events (service, endpoint,
   status code, latency, user, region, with a realistic error rate) and writes
   them as JSON to the **Bronze** S3 tier, partitioned by service and time.
   Bronze is immutable: raw data is never edited, only appended — so it is always
   possible to reprocess from source.

2. **Transformation (Bronze → Silver).** A PySpark job, developed locally and
   deployed to **AWS Glue 5.0**, reads the raw JSON with an *explicit schema*,
   parses timestamps, derives analytical columns (event date/hour, error flags),
   filters records that fail data-quality checks, and **deduplicates on
   `event_id`**. Output is compressed, partitioned **Parquet** in the Silver tier.

3. **Cataloging.** A **Glue crawler** registers the Silver Parquet — schema and
   partitions — in the Glue Data Catalog, making it queryable through Athena.

4. **Modeling (Silver → Gold).** **dbt** (Athena adapter) transforms Silver into
   business marts: hourly service KPIs, daily active users, error analytics, and a
   **slowly changing dimension (SCD Type 2)** snapshot of users, implemented as an
   Iceberg table. dbt runs data-quality tests and produces lineage documentation.

5. **Serving.** A **FastAPI** backend queries the Gold marts through Athena and
   exposes analytics as JSON; a **Chart.js** dashboard renders them. Query results
   are cached in memory with a short TTL.

6. **Orchestration.** An **Airflow** DAG runs steps 1–4 in dependency order, on a
   schedule, with retries and failure alerting.

---

## 4. Key design decisions & trade-offs

This section is the heart of the design — the decisions that shaped the system
and the reasoning behind each.

### 4.1 Medallion architecture (Bronze / Silver / Gold)

**Decision:** Separate raw, cleaned, and business tiers rather than transforming
in one step.

**Why:** Each tier has a single, clear responsibility and contract. Raw data is
preserved immutably (Bronze), so any downstream logic change can be reprocessed
from source. Cleaning is centralized once (Silver) and reused by every consumer.
Business logic lives in a dedicated layer (Gold) without polluting the cleaning
step.

**Trade-off:** More storage and more pipeline stages versus a single
transformation. Accepted because storage is cheap and the separation pays for
itself in maintainability and reprocessability.

### 4.2 Parquet + partitioning for Silver/Gold

**Decision:** Store cleaned data as partitioned, columnar Parquet rather than JSON.

**Why:** Athena bills per terabyte scanned. Columnar storage enables column
pruning (read only needed columns); partitioning enables partition pruning (read
only relevant time/service slices); compression shrinks data 3–5×. Together these
cut query cost by roughly an order of magnitude and make queries faster.

**Trade-off:** Parquet is not human-readable and has write-time overhead.
Irrelevant here — Silver/Gold are machine-consumed.

### 4.3 Local-first Spark development

**Decision:** Develop and test the PySpark transformation locally, then deploy the
*identical* `transform()` logic to Glue.

**Why:** Glue costs money and takes 1–2 minutes to provision per run; local Spark
is free and iterates in seconds. Keeping the transformation logic identical means
local correctness transfers to the cloud.

**Trade-off:** Requires a local Spark environment and discipline to keep the two
entry points in sync. Worth it for fast, free iteration.

### 4.4 Idempotency everywhere

**Decision:** Make every stage safe to re-run — deduplicate on `event_id`, use
deterministic transformations, write with overwrite semantics.

**Why:** Idempotency is the prerequisite for safe retries. Because each stage
produces the same result whether it runs once or five times, Airflow can retry a
failed task without creating duplicates or corrupting data.

**Trade-off:** Deduplication adds processing cost. Negligible, and essential for
a reliable pipeline.

### 4.5 dbt on Athena (not Snowflake)

**Decision:** Run dbt against Athena, keeping the entire lakehouse on one stack.

**Why:** The data already lives in S3 and is catalogued in Glue. dbt-athena issues
`CREATE TABLE AS` / `CREATE VIEW`, transforming in place — no data movement, no
second platform, no extra cost. The lakehouse stays coherent end to end.

**Trade-off:** Snowflake is more universally recognized and has a smoother
developer experience; the Athena adapter is more finicky. Accepted for coherence
and cost; the dbt *skills* (models, refs, tests, materializations) are
warehouse-portable, so a Snowflake variant is a small future add.

### 4.6 SCD Type 2 via Iceberg

**Decision:** Implement the user dimension's history with a dbt snapshot on an
Iceberg table.

**Why:** SCD Type 2 requires *updating* old rows to close their validity period.
Standard Hive-format tables on Athena are append/overwrite only and cannot do
row-level updates; Iceberg supports them. So snapshots use `table_type: iceberg`.

**Trade-off:** Iceberg adds a small amount of complexity over plain Parquet.
Necessary for correct SCD2 semantics.

### 4.7 Local Airflow (not MWAA)

**Decision:** Run Airflow locally in Docker (Astronomer runtime), orchestrating
the remote AWS services, rather than using managed MWAA.

**Why:** MWAA runs a continuously-on environment costing ~$350+/month. Local
Airflow is free and teaches and demonstrates the same skills — the DAG, operators,
retries, scheduling, alerting — while orchestrating the real AWS services via the
Amazon provider operators.

**Trade-off:** Local Airflow is not a deployed, always-on scheduler. For a
portfolio and for development this is the right call; production would lift the
same DAG into MWAA (or a self-hosted cluster) unchanged.

### 4.8 dbt isolated inside Airflow

**Decision:** Install dbt in a dedicated virtual environment inside the Airflow
image and invoke it from a Bash task.

**Why:** dbt and Airflow pin conflicting dependency versions; installing dbt into
Airflow's environment breaks the image. Isolation avoids the conflict cleanly.

**Trade-off:** Slightly more image-build complexity. The production-grade
alternative is `astronomer-cosmos` (which renders the dbt DAG as native Airflow
tasks) or running dbt in a separate container — both noted as future improvements.

### 4.9 Caching in the serving layer

**Decision:** Cache Gold-mart query results in memory with a short TTL.

**Why:** Athena queries take seconds and cost per run. A metrics dashboard does
not need second-by-second freshness, so caching makes repeat loads instant and
avoids re-billing Athena on every page view.

**Trade-off:** Data can be up to the TTL stale — acceptable for operational
metrics; for real-time needs the TTL shrinks or a streaming path replaces it.

### 4.10 Infrastructure as code

**Decision:** Define the data lake and Glue resources in Terraform.

**Why:** The whole environment is reproducible from code, version-controlled, and
documented by its own definitions. It can be torn down and rebuilt identically.

**Trade-off:** Up-front effort over click-ops. Pays off immediately in
reproducibility and is non-negotiable for any serious platform.

---

## 5. Reliability & data quality

- **Idempotent stages** make retries safe (see 4.4).
- **Explicit schema** on read surfaces malformed data instead of silently
  mis-typing it.
- **Data-quality filters** in the Silver transform drop records missing critical
  fields (in production these would be quarantined rather than dropped).
- **dbt tests** (generic: `unique`, `not_null`; and a custom singular test on
  error-rate bounds) run on every build and fail before bad data reaches consumers.
- **Airflow retries + failure alerting** handle transient failures and surface
  hard ones.
- **CI** (GitHub Actions) validates Python, the dbt project, and Terraform on
  every push, catching errors before they merge.

---

## 6. Cost design

The platform is deliberately cheap to run — total cost is a fraction of a dollar
per month.

- **Ephemeral Glue jobs** — spin up, run, shut down; no idle cost.
- **Athena over partitioned Parquet** — minimal data scanned per query.
- **Local Airflow** instead of always-on MWAA (~$350+/month avoided).
- **Serving-layer caching** — fewer Athena queries.
- **S3 lifecycle rules** — older data transitions to cheaper storage classes.

Cost-consciousness is treated as a first-class design constraint, not an
afterthought.

---

## 7. Security

- **No credentials in code or version control.** Configuration (region, buckets)
  is non-secret; credentials come from the standard AWS credential chain and are
  gitignored where stored locally.
- **CI runs credential-free** — `dbt parse` and `terraform validate` do not
  connect to AWS, so no secrets live in the pipeline.
- **Production hardening (planned):** replace long-lived IAM access keys with
  short-lived, least-privilege roles (e.g. an MWAA execution role, or OIDC role
  assumption in CI) scoped to only the required Glue/Athena/S3 actions. This
  follows directly from a real lesson during development, where a long-lived key
  had to be rotated after exposure.

---

## 8. Scalability & path to production

The current design runs at small scale on a single developer machine plus AWS.
Scaling it up is mostly a matter of configuration, because the architecture itself
is already the production pattern.

| Concern | Current | Production path |
|---------|---------|-----------------|
| Orchestration | Local Airflow (Docker) | Lift the same DAG into MWAA or a self-hosted cluster |
| Compute | Glue 2-DPU minimum | Increase DPUs / enable autoscaling for larger volumes |
| Ingestion | Batch generator | Replace with real sources; add streaming (Kinesis) for real-time |
| dbt execution | Bash task, isolated venv | `astronomer-cosmos` for native task-level dbt lineage |
| Scheduling | Manual trigger (cost control) | Cron/`@daily` or asset-driven scheduling |
| Credentials | Static IAM key | Short-lived least-privilege roles / OIDC |
| Serving | Local FastAPI | Containerize and deploy (ECS/Fargate); add auth |
| Alerting | Logged callback | Route to Slack / PagerDuty / email |

Because the pipeline is idempotent, partitioned, and defined as code, scaling
volume mostly means more compute and a real schedule — not a redesign.

---

## 9. Future work

- A **streaming path** (Kinesis + Spark Structured Streaming) alongside the batch
  pipeline for real-time metrics.
- A **Snowflake variant** of the dbt project, to demonstrate warehouse portability.
- **astronomer-cosmos** to render the dbt DAG as native Airflow tasks with
  per-model lineage and retries.
- **Deployed serving layer** (containerized FastAPI on ECS/Fargate) with
  authentication.
- **Real alerting** integrations (Slack/PagerDuty) and richer observability
  (run metrics, data freshness monitoring, anomaly alerts).

---

## 10. Summary

PipelineWatch is a coherent, cost-efficient, end-to-end data platform that
exercises the full modern data stack: ingestion to S3, distributed transformation
on Spark/Glue, analytics engineering with dbt, orchestration with Airflow, and a
served analytics dashboard — all reproducible from Terraform, validated by CI, and
designed around correctness, idempotency, and cost. Its design choices favor
simplicity, clear contracts between tiers, and the ability to explain and defend
every decision — which is exactly what a production data platform, and a strong
engineering portfolio, both require.
