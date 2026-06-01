# Copy these into the root module's backend "s3" block (infra/terraform/versions.tf).

output "state_bucket_name" {
  description = "S3 bucket holding the root module's remote state."
  value       = aws_s3_bucket.state.id
}

output "lock_table_name" {
  description = "DynamoDB table used for state locking."
  value       = aws_dynamodb_table.locks.name
}
