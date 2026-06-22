# ============================================================
# PipelineWatch Data Lake module
# Provisions three S3 buckets (Bronze, Silver, Gold) with
# security defaults and lifecycle policies.
# ============================================================

# -------------------- Inputs --------------------

variable "project" {
  type        = string
  default     = "pipelinewatch"
  description = "Project name used as a prefix for resource names"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment: dev, staging, or prod"
}

# -------------------- Helpers --------------------

# Random suffix so bucket names are globally unique across all AWS accounts.
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# -------------------- The three buckets --------------------

resource "aws_s3_bucket" "bronze" {
  bucket = "${var.project}-bronze-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.project}-silver-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.project}-gold-${var.environment}-${random_id.bucket_suffix.hex}"
}

# -------------------- Block all public access --------------------

resource "aws_s3_bucket_public_access_block" "bronze" {
  bucket                  = aws_s3_bucket.bronze.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "silver" {
  bucket                  = aws_s3_bucket.silver.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "gold" {
  bucket                  = aws_s3_bucket.gold.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -------------------- Versioning on Bronze --------------------

# Bronze versioning is a safety net for raw data — if a Glue job
# accidentally overwrites a file, we can restore the previous version.
resource "aws_s3_bucket_versioning" "bronze" {
  bucket = aws_s3_bucket.bronze.id
  versioning_configuration {
    status = "Enabled"
  }
}

# -------------------- Lifecycle policy on Bronze --------------------

# Bronze raw data ages out cheaply:
#  - First 90 days: Standard (hot, fast access)
#  - Days 90 - 365: Standard-IA (cheaper, slower retrieval)
#  - Day 365+: Glacier (cold archive, ~1/5 the cost of Standard)
# Old object versions (from versioning) expire after 30 days.
resource "aws_s3_bucket_lifecycle_configuration" "bronze" {
  bucket = aws_s3_bucket.bronze.id

  rule {
    id     = "age-based-tiering"
    status = "Enabled"

    filter {
      prefix = "bronze/"
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# -------------------- Outputs --------------------

output "bronze_bucket" {
  value       = aws_s3_bucket.bronze.id
  description = "Name of the Bronze tier bucket"
}

output "silver_bucket" {
  value       = aws_s3_bucket.silver.id
  description = "Name of the Silver tier bucket"
}

output "gold_bucket" {
  value       = aws_s3_bucket.gold.id
  description = "Name of the Gold tier bucket"
}
