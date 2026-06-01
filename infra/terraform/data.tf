# Lookups that keep account-specific and image-specific values out of the source.
# Using data sources (instead of hardcoded IDs) is what lets this box be rebuilt
# from code in any matching account/region — the Phase 2 reproducibility goal.

# The account ID, used to scope the IAM inline policy's Parameter Store ARN.
data "aws_caller_identity" "current" {}

# The account's default VPC — the hand-built Phase 1 box lived here, so we reuse it.
data "aws_vpc" "default" {
  default = true
}

# The default subnet in the chosen AZ. We pin the AZ (var.availability_zone) on
# purpose: us-east-1e does NOT offer t3.medium, so a blind pick could land there.
data "aws_subnets" "default_az" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "availability-zone"
    values = [var.availability_zone]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# Latest Canonical Ubuntu 24.04 LTS (amd64 — t3.medium is Intel, not Graviton).
# var.ami_id can override this for byte-for-byte parity with the Phase 1 image.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}
