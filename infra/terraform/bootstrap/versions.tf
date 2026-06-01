# Bootstrap config — provider + version pins.
#
# This config intentionally uses LOCAL state (no backend block). It creates the
# S3 bucket and DynamoDB lock table that back the *root* module's remote state,
# so it cannot store its own state in that bucket (the chicken-and-egg problem).
# Keep the small local terraform.tfstate it produces.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "LinkShrink"
      ManagedBy = "Terraform"
      Component = "tf-state-backend"
    }
  }
}
