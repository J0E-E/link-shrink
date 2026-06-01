# Root module inputs. Defaults mirror the hand-built Phase 1 environment so later
# epics (5: compute/network/IAM, 6: DNS/ECR) recreate the same box from code.

variable "aws_region" {
  description = "AWS region the LinkShrink stack runs in."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for the application host."
  type        = string
  default     = "t3.medium"
}

variable "domain" {
  description = "Public domain served by the stack."
  type        = string
  default     = "link-shrink.org"
}
