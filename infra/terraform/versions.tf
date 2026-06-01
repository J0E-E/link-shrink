# Root module — version pins + remote state backend.
#
# The backend points at the S3 bucket and DynamoDB lock table created by the
# bootstrap config (infra/terraform/bootstrap/). Run the bootstrap apply BEFORE
# `terraform init` here, or init will fail to find the bucket.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  backend "s3" {
    bucket         = "linkshrink-tfstate-310199963650"
    key            = "linkshrink/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "linkshrink-tf-locks"
    encrypt        = true
  }
}
