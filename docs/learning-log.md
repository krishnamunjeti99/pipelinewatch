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