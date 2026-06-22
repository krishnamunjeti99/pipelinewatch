# ============================================================
# Glue infrastructure for the Bronze -> Silver transformation
# ============================================================

# -------------------- IAM role Glue runs under --------------------

# Trust policy: allow the Glue service to assume this role.
resource "aws_iam_role" "glue" {
  name = "${var.project}-glue-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# AWS-managed base policy: CloudWatch logs, Glue catalog access, etc.
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Explicit S3 access to OUR buckets (the managed policy only covers
# buckets named aws-glue-*, which ours are not).
resource "aws_iam_role_policy" "glue_s3" {
  name = "glue-s3-access"
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.bronze.arn, "${aws_s3_bucket.bronze.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.silver.arn, "${aws_s3_bucket.silver.arn}/*"]
      }
    ]
  })
}

# -------------------- Glue Catalog database --------------------

# Note: Glue database names use underscores, not hyphens.
resource "aws_glue_catalog_database" "main" {
  name = "${var.project}_${var.environment}"
}

# -------------------- Upload the Glue script to S3 --------------------

# The Glue job reads its script from S3. The etag triggers re-upload
# whenever the local script changes.
resource "aws_s3_object" "glue_script" {
  bucket = aws_s3_bucket.silver.id
  key    = "scripts/bronze_to_silver_glue.py"
  source = "${path.module}/../../../transformations/spark_jobs/bronze_to_silver_glue.py"
  etag   = filemd5("${path.module}/../../../transformations/spark_jobs/bronze_to_silver_glue.py")
}

# -------------------- The Glue job --------------------

resource "aws_glue_job" "bronze_to_silver" {
  name              = "${var.project}-bronze-to-silver-${var.environment}"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X" # 1 DPU each
  number_of_workers = 2      # minimum for a Spark job = 2 DPU total

  command {
    name            = "glueetl" # "glueetl" = Spark ETL job
    script_location = "s3://${aws_s3_bucket.silver.id}/scripts/bronze_to_silver_glue.py"
    python_version  = "3"
  }

  default_arguments = {
    "--bronze_path"                      = "s3://${aws_s3_bucket.bronze.id}/bronze/"
    "--silver_path"                      = "s3://${aws_s3_bucket.silver.id}/silver/"
    "--TempDir"                          = "s3://${aws_s3_bucket.silver.id}/tmp/"
    "--job-language"                     = "python"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}

# -------------------- Outputs --------------------

output "glue_job_name" {
  value       = aws_glue_job.bronze_to_silver.name
  description = "Name of the Bronze->Silver Glue job"
}

output "glue_database" {
  value       = aws_glue_catalog_database.main.name
  description = "Glue Catalog database name"
}