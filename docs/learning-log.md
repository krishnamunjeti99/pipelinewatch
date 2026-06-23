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