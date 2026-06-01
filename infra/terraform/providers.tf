# AWS provider. Region comes from var.aws_region (defaults to us-east-1).
# default_tags stamps every taggable resource so the LinkShrink stack is easy to
# find and account for in the console and Cost Explorer.

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "LinkShrink"
      ManagedBy = "Terraform"
    }
  }
}
