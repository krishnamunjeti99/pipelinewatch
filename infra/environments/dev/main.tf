# ============================================================
# Dev environment for PipelineWatch
# Entry point for `terraform apply`; composes shared modules.
# ============================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# AWS provider configured for Mumbai region.
# default_tags applies these tags to every resource — essential for
# cost tracking and audit. Most junior engineers forget this.
provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      project     = "pipelinewatch"
      environment = "dev"
      managed_by  = "terraform"
    }
  }
}

# Call the data-lake module with dev-environment values.
module "data_lake" {
  source = "../../modules/data-lake"

  project     = "pipelinewatch"
  environment = "dev"
}

# Expose module outputs at the root so `terraform output` shows them
# and so other tooling can read them.
output "bronze_bucket" {
  value = module.data_lake.bronze_bucket
}

output "silver_bucket" {
  value = module.data_lake.silver_bucket
}

output "gold_bucket" {
  value = module.data_lake.gold_bucket
}
output "glue_job_name" {
  value = module.data_lake.glue_job_name
}

output "glue_database" {
  value = module.data_lake.glue_database
}
output "silver_crawler_name" {
  value = module.data_lake.silver_crawler_name
}

