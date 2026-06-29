# Learning Log

## 2026-06-15 — Phase 0 complete

**What I did:**
- Created AWS account with root MFA enabled.
- Created a daily-use admin IAM user (krishna-admin) with MFA enabled.
- Configured AWS CLI in ap-south-1 (Mumbai) and verified with `aws sts get-caller-identity`.
- Set up WSL2 with Ubuntu, installed Python, Git, AWS CLI, Terraform, Docker.
- Created the project scaffolding at ~/projects/pipelinewatch.
- Set up SSH authentication with GitHub and pushed the initial commit.

**Concepts learned:**
- IAM root vs IAM user. Root is for billing emergencies only; daily work uses a least-privilege IAM user with MFA.
- Why MFA assignment requires an already-MFA-authenticated session (the chicken-and-egg bootstrap problem AWS solves by requiring root the first time).
- WSL2 file system performance: Linux home directory is fast, /mnt/c/ is slow.
- SSH key authentication for Git: ed25519 keys are modern and secure.

**Gotchas I hit:**
- "You need permissions" error when trying to assign MFA to my IAM user from that user's own session. Fix: do it from the root account, just once.
- Docker permission denied initially because my user wasn't in the docker group. Fix: `sudo usermod -aG docker $USER` and restart the shell.
- `code` command not found until VS Code + WSL extension were installed on Windows.

**Interview answers locked in:**

*Q: How do you secure an AWS account?*
- Enable MFA on the root account immediately.
- Never use root for daily work; create an admin IAM user with its own MFA.
- Never commit access keys; rotate them periodically.
- Use IAM roles (not users) for services and EC2 instances.
- Apply least-privilege: specify resources explicitly, avoid `"*"` in policies.
- Set billing alarms before any infrastructure is provisioned.

*Q: What's the difference between an IAM user and an IAM role?*
- A user has long-term credentials (password, access keys) and represents a person or external system.
- A role has no long-term credentials; it's assumed temporarily via STS, with short-lived session tokens.
- Services (Lambda, EC2, Glue) should use roles, never embedded user keys.

## Week 1 wrap-up — Data lake foundations complete

**What I built this week**

End-to-end synthetic-data ingestion pipeline:
- Python generator (`ingestion/batch_generator/generate_logs.py`) that produces realistic application telemetry events with weighted status code distribution, sorted timestamps, and Hive-style partition keys.
- Backfill mode (`--backfill N --events M`) for generating historical data spanning N hours.
- Terraform module (`infra/modules/data-lake/`) provisioning 3 S3 buckets (Bronze, Silver, Gold), public access blocked, versioning on Bronze, lifecycle policy transitioning data Standard → IA (90d) → Glacier (365d).
- Root environment (`infra/environments/dev/`) configured for ap-south-1 with default tags applied to every resource.
- ~72,000 events written across 24 hours of backfill, partitioned by service and hour.

**Concepts truly locked in (vs. just heard about)**

- **Object storage vs. filesystem**: S3 has no directories, only flat keys. The "folder" structure is a UI convention.
- **Global bucket name uniqueness**: bucket names must be unique across all of AWS. Random suffix is essential.
- **Hive-style partitioning**: `service=X/year=Y/month=Z/...` is recognized by Glue, Athena, and Spark automatically. Critical for query cost reduction.
- **Lifecycle policies as cost optimization**: ~80% cost saving on aged data with no operational overhead.
- **Versioning is per-tier**: only worth the cost where data is irrecoverable.
- **The medallion architecture** (Bronze/Silver/Gold) maps cleanly to data quality and access patterns: raw → cleaned → business-ready.
- **Terraform's plan/apply contract**: plan shows the diff, apply executes it. Reading plan output before applying is non-negotiable.
- **Modules vs. environments**: modules are reusable building blocks; environments compose them with environment-specific values.
- **Default tags via provider config**: every resource auto-tagged for cost tracking. Easy to forget; critical to remember.
- **IAM bootstrap problem**: MFA assignment requires an MFA-authenticated session, solvable only via root.

**Gotchas I hit and what I learned**

- **S3 Select is deprecated**: AWS now points to Athena for querying S3 data, even individual files. The architectural reason: file-level query APIs can't take advantage of partitioning, predicate pushdown across files, or the Glue Data Catalog. Lesson: don't query files; query tables.
- **Bash silently drops unset variables**: `python script $VAR --flag` becomes `python script --flag` if `$VAR` is empty, with no warning. Always confirm shell variables with `echo "[$VAR]"` before debugging the program that consumed them.
- **Docker WSL integration is a separate toggle**: the docker command isn't available in WSL until you flip the integration switch in Docker Desktop settings.
- **VS Code `code` command needs the WSL extension first**: installing VS Code on Windows alone isn't enough; the WSL extension exposes the `code` shim into your Linux PATH.
- **Python REPL imports need `__init__.py`**: a directory isn't an importable package without it.

**Interview answers I can now give cleanly**

*Q: How would you structure data on S3 for an analytics workload?*

Three tiers in a medallion architecture: Bronze for raw landing (append-only, partitioned by date/source, lifecycle-policed to Glacier), Silver for cleaned and schema-enforced data (Parquet, partitioned for query efficiency), Gold for business-level marts queryable by BI tools. Hive-style partition keys (`event_date=YYYY-MM-DD/service=X/`) so query engines automatically recognize partitions. Public access blocked at the bucket level. Versioning only where data is irrecoverable.

*Q: Walk me through your Terraform structure.*

Reusable modules under `infra/modules/` — one per concern like data-lake, streaming, orchestration. Environment configurations under `infra/environments/{dev,staging,prod}/` each call the modules with environment-specific values. Provider configuration sets default tags applied to every resource for cost tracking. State file is local for dev work but moves to S3 with DynamoDB locking in production. Plan output is reviewed in pull requests; apply happens on merge to main.

*Q: How does Terraform handle dependencies between resources?*

It builds a DAG from references between resources. For example, my Bronze bucket has a versioning resource that references `aws_s3_bucket.bronze.id` — Terraform sees that reference, creates the bucket first, then versioning. Apply walks the graph in dependency order, parallelizing where possible. I can also declare explicit dependencies with `depends_on` for cases Terraform can't infer (e.g. an IAM policy that grants permissions needed at startup).

*Q: What's the difference between an IAM user and role?*

A user has long-term credentials — password, access keys — and represents a person or external system. A role has no long-term credentials; it's assumed temporarily via `sts:AssumeRole`, and AWS returns short-lived session tokens valid 15 minutes to 12 hours. Services like Lambda, EC2, and Glue should always use roles, never embedded user keys, because rotated session credentials are inherently safer than long-lived keys. The trust policy says who can assume the role; the permissions policy says what the role can do once assumed.

**Week 1 self-assessment (be honest)**

- [ ] I understand why S3 buckets need globally unique names.
- [ ] I can explain the difference between `terraform plan` and `terraform apply` to someone else.
- [ ] I can write a Hive-style partition path from memory.
- [ ] I know what `--default_tags` does and why it matters.
- [ ] I understand why the IAM MFA assignment required root the first time.
- [ ] I could rebuild the entire Bronze tier from scratch by running `terraform apply` in a fresh AWS account.
- [ ] I can explain why versioning was applied only to Bronze.
- [ ] I understand the lifecycle policy and what it does to data over time.

Check the boxes honestly. Anything unchecked is worth 10 minutes of re-reading before Week 2.

## Phase 2 Day 2 — PySpark Bronze to Silver transformation

**What I built:**
- A PySpark transformation job (transformations/spark_jobs/bronze_to_silver.py) reading Bronze JSONL, cleaning/typing/deduplicating, and writing partitioned Parquet.
- Set up local Spark (Java 17 + pyspark 3.5.1) for free, fast iteration before deploying to Glue.
- Verified output: ~Nx smaller than JSON despite adding 5 derived columns.

**Concepts locked in:**
- Explicit schema beats inference: faster, deterministic, catches bad data. Inference requires a full scan and can guess types wrong.
- partitionBy writes Hive-style partitions and removes partition columns from file contents (encoded in path instead).
- _SUCCESS marker file signals job completion to downstream tools.
- dropDuplicates on a unique key = idempotency; the pipeline is safe to re-run.
- Separating transform() (pure, no IO) from main() (IO) makes the logic unit-testable.
- Snappy compression: fast, good ratio, the default choice for Parquet.

**Why local-first:** Glue costs money and is slow to iterate. Develop locally with a data sample, deploy to Glue once the logic is right. This is standard professional practice.

**Interview answers:**

*Q: Walk me through a transformation job you've written.*
- Read raw JSON with an explicit schema (no inference — deterministic and faster).
- Parse timestamps, derive date/hour columns for partitioning and analysis.
- Precompute boolean flags (is_error) so downstream queries are simpler.
- Apply data-quality filters dropping rows with null critical fields.
- Deduplicate on event_id for idempotency.
- Write partitioned Parquet (by date and service) with snappy compression.

*Q: Why Parquet over JSON for the cleaned tier?*
- Columnar: queries read only needed columns (column pruning).
- Row-group statistics enable predicate pushdown (skip non-matching chunks).
- 3-5x compression even while adding columns.
- Result: dramatically cheaper and faster analytical queries.

*Q: How do you make a pipeline idempotent?*
- Deduplicate on a stable unique key (event_id) so re-runs don't create duplicates.
- Use overwrite mode on partitions so re-processing a partition replaces rather than appends.
- Deterministic transformations: same input always yields same output.

## Phase 2 Day 4 — Crawler + Athena: the data lake becomes queryable

**What I built:**
- Glue Crawler (Terraform) that scans Silver Parquet, infers schema, detects event_date/service partitions, and registers a table in the Glue Catalog.
- Configured Athena query result location.
- Ran first SQL queries against the Silver table.

**Concepts locked in:**
- A crawler turns S3 files into a queryable table by registering schema + partitions in the Catalog. Without it, Athena doesn't know the data exists.
- Partition keys (event_date, service) become filterable columns even though they live in the folder path, not the files.
- Athena = serverless Presto/Trino over S3, using the Glue Catalog as metastore. $5/TB scanned.
- "Data scanned" = cost. Column pruning (Parquet) and partition pruning (WHERE on partition keys) both reduce it.
- Crawler has a 10-min minimum charge (~$0.15/run) — don't run it in a loop.

**The payoff:** P95 latency by service across the entire dataset, in ~2 seconds, as one SQL query. Same analysis done manually with grep earlier took 20 minutes for one hour of one service.

**Interview answers:**

*Q: How does data in S3 become queryable with SQL?*
- A crawler (or manual DDL) registers the schema, partitions, format, and location in the Glue Data Catalog.
- Athena reads the catalog to know the table's structure and where its files live.
- Athena's Presto engine reads the Parquet from S3 in parallel and runs the SQL.
- Storage (S3) and compute (Athena) are fully separated.

*Q: How do you reduce Athena query cost?*
- Use columnar Parquet so queries read only needed columns (column pruning).
- Partition on commonly-filtered dimensions so queries scan only relevant prefixes (partition pruning).
- Select specific columns, not SELECT *.
- Use compression and avoid many small files.
- Materialize hot aggregates with CTAS.

*Q: What's the role of the Glue Data Catalog?*
- Central metadata store: schema, partition keys, file format, S3 location per table.
- Shared by Athena, Redshift Spectrum, EMR, Glue, and external tools.
- The single integration point that makes a lakehouse work.

## Phase 2 wrap-up — Silver tier complete: the data lake is queryable

**What I built across Phase 2**

A complete Bronze → Silver → queryable pipeline:
- PySpark transformation (developed and tested locally, deployed to AWS Glue 5.0) that cleans, types, deduplicates, and enriches raw JSON into partitioned Parquet.
- Glue infrastructure in Terraform: IAM role, Glue Catalog database, script upload, Glue job, Glue crawler.
- Silver tier: partitioned Parquet (event_date, service), ~Nx smaller than the Bronze JSON.
- Glue Catalog table registered by the crawler, queryable via Athena.
- A library of analytical SQL: error rates, P95/P99 latency, traffic by hour, top users, window functions, CTEs, ranking.

**Concepts truly locked in**

- Local-first development: build/test Spark locally (free, fast), deploy to Glue (paid, managed). Identical transform() logic both places.
- Glue jobs are ephemeral (no idle cost); Dev Endpoints/Interactive Sessions are not (bill shock risk).
- Glue 5.0 = Spark 3.5.4 + Python 3.11; matched my local Spark so code ported unchanged.
- Parquet columnar format: column pruning + predicate pushdown + compression = dramatically cheaper queries.
- The crawler registers schema AND specific partitions in the Catalog; Athena reads partition lists from the Catalog, not S3.
- New data isn't auto-visible: must re-crawl, MSCK REPAIR TABLE, or use partition projection (the scalable answer).
- Crawlers infer partition columns as varchar — event_date came through as string, not date.
- Athena = serverless Presto over S3; $5/TB scanned; "data scanned" IS the cost.
- Window functions (SUM/RANK/ROW_NUMBER OVER PARTITION BY ORDER BY), CTEs, self-joins — the analytical SQL interviewers test.

**Gotchas I hit**

- Duplicate Terraform outputs (module vs root) — module outputs reference resources, root outputs reference the module.
- event_date registered as varchar by the crawler — comparing to DATE literal failed; fix with string comparison (still prunes) or CAST (can defeat pruning).
- VS Code WSL save "Canceled" glitch — reload window or write from terminal.

**The Phase 2 payoff**

P95 latency by service across the entire dataset, as one SQL query, in ~2 seconds. The same analysis done manually with grep in Phase 1 took 20 minutes for one hour of one service. This is why the medallion architecture exists.

**Interview answers I can now give**

*Q: Walk me through an ETL pipeline you've built.*
Raw JSON application logs land in an S3 Bronze tier, partitioned by service and hour. A PySpark job on AWS Glue reads them with an explicit schema, parses timestamps, derives analytical columns, applies data-quality filters, deduplicates on a unique key for idempotency, and writes partitioned Parquet to a Silver tier. A Glue crawler registers the schema and partitions in the Data Catalog, making the data queryable through Athena with standard SQL. Everything is provisioned in Terraform.

*Q: Why convert JSON to Parquet?*
Columnar storage enables column pruning and predicate pushdown, and compresses 3-5x better. On Athena, which bills per terabyte scanned, this cuts query cost by an order of magnitude while making queries faster.

*Q: How does new data become visible to Athena?*
Athena reads the partition list from the Glue Catalog, so new partitions aren't automatically visible. Options: re-run the crawler (convenient), MSCK REPAIR TABLE (manual), or partition projection (computes partition locations from a pattern — the scalable production answer).

*Q: Difference between ROW_NUMBER, RANK, and DENSE_RANK?*
ROW_NUMBER assigns unique sequential numbers regardless of ties. RANK gives tied rows the same rank but leaves gaps afterward. DENSE_RANK gives tied rows the same rank with no gaps.

**Phase 2 self-assessment**
- [ ] I can explain why Parquet is cheaper to query than JSON.
- [ ] I can deploy a PySpark job to Glue and explain the wrapper boilerplate.
- [ ] I understand why new data isn't auto-visible to Athena and the three fixes.
- [ ] I can write a window function and explain PARTITION BY / ORDER BY / frame.
- [ ] I can explain the crawler's role and why it inferred event_date as varchar.
- [ ] I could rebuild this entire pipeline in a fresh AWS account from my Terraform.


## Phase 3 Day 2 — dbt + Athena setup, first model

**What I built:**
- Separate dbt environment (Python 3.12 via uv) to avoid the 3.14 incompatibility.
- Installed dbt-athena (official dbt Labs adapter).
- Created the dbt project: dbt_project.yml, staging/marts folders, materialization defaults.
- Configured the Athena connection profile in ~/.dbt/profiles.yml (out of the repo).
- Declared the Silver table as a dbt source.
- Wrote and ran stg_events — my first dbt model — which dbt built as an Athena view in a new pipelinewatch_gold Glue database.

**Concepts locked in:**
- dbt-athena issues CREATE VIEW / CREATE TABLE AS to Athena; data lives in S3, catalogued in Glue — stays in my lakehouse.
- A model is just a SELECT; the filename becomes the object name; dbt handles all DDL.
- source() references data dbt didn't create; declared in sources.yml.
- profiles.yml (connection, in ~/.dbt/) is separate from dbt_project.yml (project config, in repo). Credentials never committed.
- Materialization is set per folder: staging=view, marts=table.
- dbt debug validates the connection before running anything.

**Gotcha:** dbt-athena supports Python up to 3.13; my 3.14 venv would not work, so dbt gets its own 3.12 environment (also best practice).

**Interview answers:**

*Q: What is dbt and how does it fit an AWS lakehouse?*
- dbt is the transformation (T) layer in ELT. You write SELECT statements; dbt manages DDL, dependency ordering, tests, and docs.
- With the Athena adapter, dbt issues CREATE TABLE AS / CREATE VIEW; results are Parquet in S3, catalogued in Glue.
- It transforms data in-place in the lake, no data movement.

*Q: How does dbt know what order to build models in?*
- From ref() and source() calls. dbt builds a DAG from these references and builds in dependency order automatically.

*Q: Where do connection credentials live in a dbt project?*
- In profiles.yml, conventionally in ~/.dbt/, kept out of version control. dbt_project.yml (in the repo) references the profile by name.

## Phase 3 Day 3 — Gold marts with tests and documentation

**What I built:**
- Three Gold marts on top of stg_events, materialized as tables (real Parquet in the Gold bucket):
  - mart_service_hourly_kpis: volume, error rate, p50/p95/p99 latency, unique users per service/date/hour.
  - mart_daily_active_users: distinct active users + requests per user per service per day.
  - mart_error_analytics: error breakdown by service/endpoint/status_code.
- Data tests (unique, not_null) on staging and marts via schema YAML.
- Generated the dbt docs site with the interactive lineage DAG.

**Concepts locked in:**
- ref() builds the DAG: marts reference stg_events, so dbt builds staging first, marts second — automatically.
- dbt build = run + test in DAG order, stopping on failure. The command real teams use.
- Materialization comes from the folder config (staging=view, marts=table); no per-model boilerplate needed.
- The unique test on event_id validates that Silver dedup worked — quality enforced in the pipeline, not hoped for.
- Gold marts pre-compute aggregations once at build time, so dashboards read ready data with no aggregation.
- dbt docs generate + serve produces a browsable site with descriptions, compiled SQL, and the lineage graph.

**Interview answers:**

*Q: How do you structure a dbt project?*
- Three layers: staging (light cleanup, views), intermediate (reusable building blocks), marts (business-facing tables).
- Models reference each other with ref(); dbt builds the DAG and the correct order from those references.
- Tests and documentation are declared in YAML alongside models.

*Q: What's the value of the Gold/marts layer?*
- It pre-computes business aggregations once at build time. Dashboards and analysts query ready-made tables instead of re-aggregating raw data on every request — faster and cheaper.

*Q: How does dbt enforce data quality?*
- Declarative tests (unique, not_null, accepted_values, relationships) plus custom SQL tests.
- dbt build runs them in DAG order and fails the build if data violates them, before bad data reaches consumers.

## Phase 3 Day 4 — SCD2 snapshot + custom tests

**What I built:**
- A users reference dimension as a dbt seed (seed_users.csv).
- A dbt snapshot (users_snapshot) implementing SCD Type 2 with the check strategy on plan/country.
- Demonstrated SCD2 end to end: changed two users' attributes, re-snapshotted, and saw dbt close the old records (dbt_valid_to set) and open new current ones.
- A singular (custom) data test asserting error_rate_pct stays within 0-100.

**Concepts locked in:**
- SCD Type 2 preserves history by adding a new row per change with valid_from/valid_to; NULL valid_to = current version.
- dbt snapshots implement SCD2 automatically given a strategy + unique_key + check_cols.
- check strategy compares columns to detect change; timestamp strategy uses an updated_at column.
- Dimensions typically come from operational/reference systems (modeled here as a seed), distinct from event facts.
- dbt 1.9+ uses YAML snapshot definitions; the old .sql config block with target_schema is deprecated.
- On Athena, snapshots require table_type: iceberg because SCD2 needs row-level updates, which Hive tables don't support but Iceberg does.
- Two test types: generic (declared in YAML: unique, not_null) and singular (custom SQL returning rows = failure).
- Source freshness (loaded_at_field + freshness block) detects stale upstream data.

**Interview answers:**

*Q: Explain Slowly Changing Dimensions and how you'd implement Type 2.*
- A dimension's attributes change over time (a user upgrades plan). Type 1 overwrites (no history); Type 2 preserves it by adding a new row per change with valid_from/valid_to/is_current, so you can reconstruct any record's state at any point in time.
- In dbt, a snapshot with strategy + unique_key + check_cols implements Type 2 automatically: on each run it closes changed records and inserts new versions.

*Q: How do you enforce data quality in dbt?*
- Generic tests in YAML (unique, not_null, accepted_values, relationships) and singular tests as custom SQL that should return zero rows.
- dbt build runs them in DAG order and fails before bad data reaches consumers.

*Q: How would you detect that an upstream data source stopped updating?*
- dbt source freshness with a loaded_at_field and freshness thresholds; it warns/errors when the newest record exceeds the allowed staleness.

## Phase 3 wrap-up — Gold tier complete: analytics engineering with dbt

**What I built across Phase 3**

A complete, tested, documented Gold tier using dbt against Athena:
- dbt project configured for the Athena adapter (separate Python 3.12 env, profile out of repo).
- A staging model (stg_events) over the Silver source.
- Three business marts as materialized Parquet tables: hourly service KPIs (volume, error rate, p50/p95/p99 latency, unique users), daily active users, and error analytics.
- A users reference dimension as a seed, and an SCD Type 2 snapshot (Iceberg) tracking attribute history.
- Generic tests (unique, not_null) and a singular custom test (error-rate bounds).
- Generated documentation with the full lineage DAG.

**Concepts truly locked in**

- dbt is the T in ELT: write SELECTs, dbt manages DDL, build order (via ref/source DAG), tests, and docs.
- dbt-athena issues CREATE TABLE AS / CREATE VIEW; Gold data stays in S3, catalogued in Glue — one coherent lakehouse.
- Project layering: staging (views, light cleanup) -> marts (tables, business-facing).
- Materialization is config, not code: view vs table vs incremental vs ephemeral.
- SCD Type 2 via snapshots: strategy + unique_key + check_cols; closes old rows, opens new ones; NULL valid_to = current.
- On Athena, snapshots need table_type: iceberg (SCD2 requires row updates Hive can't do).
- dbt 1.9+ uses YAML snapshot definitions; target_schema is deprecated.
- Two test types: generic (YAML) and singular (custom SQL returning zero rows on success).
- Source freshness detects stale upstream data.
- dbt build runs the whole DAG — seeds, models, snapshots, tests — in dependency order.

**Gotchas I hit**
- Python 3.14 incompatible with dbt-athena; gave dbt its own 3.12 env (also best practice).
- Snapshots failed without table_type: iceberg on Athena.
- Old snapshot .sql config-block syntax is deprecated in dbt 1.9+; used YAML definitions.

**The Phase 3 payoff**

A fact-to-dimension join across the Gold tier (hourly KPIs joined to current user plans) returns business-ready results in seconds — from data that started as raw JSON logs. Plus a real SCD2 implementation and an auto-generated lineage DAG to show in interviews.

**Interview answers I can now give**

*Q: What is dbt and where does it fit?*
- The transformation layer in ELT. You write SELECTs; dbt manages DDL, dependency ordering via ref(), testing, and documentation. With the Athena adapter it transforms data in-place in the lake via CTAS/CREATE VIEW.

*Q: How do you structure a dbt project?*
- staging (light cleanup, views) -> intermediate (reusable logic) -> marts (business tables). Models reference each other with ref(); dbt builds the DAG and correct order automatically.

*Q: Explain SCD Type 2 and how dbt implements it.*
- New row per attribute change with valid_from/valid_to; NULL valid_to is current. dbt snapshots do this automatically given strategy, unique_key, and check_cols.

*Q: How do you ensure data quality and reproducibility in a transformation pipeline?*
- Generic + singular dbt tests run in DAG order via dbt build, failing before bad data reaches consumers; deterministic SQL transformations; version-controlled models; source freshness for staleness.

**Phase 3 self-assessment**
- [ ] I can explain dbt's role in ELT and how the Athena adapter works.
- [ ] I can describe staging/marts layering and why it matters.
- [ ] I can explain SCD Type 2 and walk through my snapshot implementation.
- [ ] I can explain the difference between generic and singular tests.
- [ ] I could rebuild the entire Gold tier from my repo in a fresh environment.

## Phase 4 Day 2 — Local Airflow up, first DAG, AWS connectivity

**What I built:**
- Local Airflow 3.x via the Astronomer astro CLI (runs in Docker, free).
- Scaffolded an orchestration/ project; added the Amazon provider for Glue operators + boto3.
- Wired AWS credentials into the containers via .env (gitignored).
- Wrote hello_pipelinewatch — a TaskFlow DAG that greets, checks AWS identity, and summarizes.
- Confirmed Airflow can authenticate to my AWS account (sts:GetCallerIdentity in task logs).

**Concepts locked in:**
- astro CLI runs full Airflow 3 locally in Docker; UI at localhost:8080.
- TaskFlow API (@dag/@task from airflow.sdk): dependencies are implicit via passing task outputs as inputs.
- schedule=None = manual trigger; catchup=False = no backfilling past dates.
- The Amazon provider package bundles boto3 and the Glue operators.
- Local Airflow orchestrates remote AWS services using credentials in the container env — no need for paid MWAA.

**Gotchas:**
- New requirements need astro dev restart to rebuild the image.
- Airflow runs ~5 containers; WSL2 may need more memory (.wslconfig).
- .env / airflow_settings.yaml hold secrets and must stay gitignored.

**Interview answers:**

*Q: How do you develop and run Airflow locally?*
- Use the astro CLI (or official Docker Compose) to run Airflow in Docker.
- DAGs live in a dags/ folder mounted into the containers; the scheduler picks them up automatically.
- Connections/credentials via environment variables or Airflow connections; secrets kept out of version control.

*Q: How are task dependencies expressed in the TaskFlow API?*
- By passing one task's return value as another's argument; Airflow infers the dependency from the data flow. Explicit ordering with >> is also available when there's no data to pass.


## Phase 4 Day 3 — Core pipeline orchestrated (generate -> glue -> crawler)

**What I built:**
- pipelinewatch_pipeline DAG orchestrating three real steps with dependencies + retries:
  - generate_logs (@task): generates fresh Bronze data via the included generator.
  - run_glue_job (GlueJobOperator): triggers the Bronze->Silver Glue job, waits for completion.
  - run_crawler (GlueCrawlerOperator): registers new Silver partitions, waits for completion.
- One trigger runs the whole AWS-native pipeline end to end (~5-7 min).

**Concepts locked in:**
- Amazon provider operators (GlueJobOperator, GlueCrawlerOperator) drive AWS declaratively instead of boto3 boilerplate.
- wait_for_completion=True makes a task block until the AWS job finishes — so downstream tasks see complete data.
- default_args retries/retry_delay add resilience to transient failures across all tasks.
- schedule=None = manual trigger; chose it deliberately to control Glue cost (each run ~$0.20).
- Dependency chain (generate >> glue >> crawler) enforces correct order.
- Code (generator) shipped into the image via include/; deps via requirements.txt.

**Cost note:** Each run = 1 Glue job (~$0.05) + 1 crawler (~$0.15) ≈ $0.20. Manual trigger only.

**Interview answers:**

*Q: How do you orchestrate AWS services from Airflow?*
- Use the Amazon provider operators (GlueJobOperator, GlueCrawlerOperator, etc.) which wrap the AWS APIs.
- wait_for_completion blocks the task until the remote job finishes, so dependencies are honored.
- Credentials come from an Airflow AWS connection or the standard boto3 credential chain (env vars locally, an execution role on MWAA).

*Q: How do you make a pipeline resilient?*
- Per-task retries with a delay handle transient failures.
- Idempotent tasks (dedup on event_id, deterministic transforms) make retries safe.
- wait_for_completion + dependency ordering prevent downstream tasks running on incomplete data.

## Phase 4 Day 4 debugging — dbt in a container: three stacked failures

1. **mmh3 wheel build failed** ("command 'cc' failed"): the slim Astro image lacked a C
   compiler. Fix: added build-essential to packages.txt.
2. **Silent dbt exit code 2**: dbt crashed during logging init (PermissionError: 'logs')
   because the host-copied project dir (UID 1000) wasn't writable by the container's
   astro user — and the crash happened before the console logger existed, so NOTHING
   printed. Diagnosed by calling dbt's cli() via Python with standalone_mode=False to
   force the traceback. Fix: --log-path /tmp/dbt_logs and --target-path /tmp/dbt_target.
3. **--profiles-dir rejected as a global flag** in dbt 1.11: used DBT_PROFILES_DIR env var
   instead. And --target-path is invalid for `debug` (only `build`).

Lesson: when a CLI exits non-zero with zero output, suspect its own logging/output
init. Bypass by invoking the entrypoint in-process to surface the real exception.

## Phase 4 wrap-up — Orchestration with Airflow

**What I built across Phase 4**

A single Airflow DAG orchestrating the entire platform end to end:
- Local Airflow 3.x via the Astronomer astro CLI (Docker), free — orchestrating remote AWS services.
- Four tasks in dependency order: generate_logs (Python) -> run_glue_job (GlueJobOperator) -> run_crawler (GlueCrawlerOperator) -> dbt_build (BashOperator on an isolated dbt venv).
- Per-task retries (2x, 2-min delay) for resilience; on_failure_callback for alerting.
- dbt running inside the image in an isolated virtualenv (avoids dependency conflicts), writing logs/target to /tmp (container-writable).
- One trigger runs the full Bronze -> Silver -> Gold pipeline (~8-12 min).

**Concepts truly locked in**
- Orchestration solves what manual scripts can't: scheduling, dependency enforcement, retries, monitoring, run history.
- DAG = directed acyclic graph of tasks; TaskFlow API infers dependencies from data flow.
- Amazon provider operators (GlueJobOperator, GlueCrawlerOperator) drive AWS declaratively; wait_for_completion blocks until the remote job finishes.
- Idempotency is the prerequisite for safe retries (dedup on event_id, deterministic transforms).
- schedule=None vs cron/preset/asset; catchup controls backfilling missed intervals; logical date vs run time.
- Running dbt in Airflow: isolate it (venv/container/cosmos) to avoid dependency conflicts.
- Failure callbacks route alerts to Slack/email/PagerDuty in production.
- Local Airflow orchestrates AWS for free; MWAA is the managed production option (~$350+/mo).

**Hard-won debugging (Day 4)**
- mmh3 needed a C compiler -> added build-essential to packages.txt.
- Silent dbt exit 2 = crash during logging init (PermissionError on 'logs' dir, host UID vs container astro user). Crash happened before the console logger existed, so nothing printed. Diagnosed via cli() with standalone_mode=False. Fixed with --log-path/--target-path to /tmp + DBT_PROFILES_DIR.
- Lesson: a CLI exiting non-zero with zero output -> suspect its own output/logging init; invoke the entrypoint in-process to surface the exception.

**Security lesson**
- Long-lived admin access keys are a liability (one got exposed during debugging and had to be rotated). Production pattern: short-lived, least-privilege IAM roles (e.g. MWAA execution role) instead of static keys in env vars.

**Interview answers I can now give**
- "Walk me through orchestrating a pipeline on Airflow" — one DAG, four tasks, dependencies, retries, alerting; Glue via provider operators with wait_for_completion; dbt in an isolated venv.
- "How do you run dbt in Airflow without dependency conflicts?" — isolated venv + Bash/ExternalPython, a separate container, or astronomer-cosmos.
- "How do you make a pipeline resilient and observable?" — retries + idempotency, failure callbacks, the UI for logs/history/durations.
- "Why local Airflow not MWAA?" — cost; local orchestrates the same AWS services for free; MWAA is the managed prod path.

**Phase 4 self-assessment**
- [ ] I can explain what orchestration adds over manual scripts.
- [ ] I can write a TaskFlow DAG and explain dependency inference.
- [ ] I can explain how Airflow drives AWS (provider operators + wait_for_completion).
- [ ] I can explain retries + idempotency and failure alerting.
- [ ] I can explain the dbt-in-Airflow isolation problem and three solutions.
- [ ] I could rebuild and run the whole pipeline from my repo.

