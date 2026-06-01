# Bootstrap inputs. Defaults match the live LinkShrink account so the backend can
# be created with `terraform apply` and no extra flags.

variable "aws_region" {
  description = "AWS region that holds the Terraform state bucket and lock table."
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name that stores the root module's remote state."
  type        = string
  default     = "linkshrink-tfstate-310199963650"
}

variable "lock_table_name" {
  description = "DynamoDB table name used for Terraform state locking."
  type        = string
  default     = "linkshrink-tf-locks"
}
