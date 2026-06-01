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

variable "availability_zone" {
  description = "AZ for the app host's subnet. us-east-1e does not offer t3.medium, so it is avoided."
  type        = string
  default     = "us-east-1a"
}

variable "ami_id" {
  description = "Override AMI for the app host. Empty uses the latest Canonical Ubuntu 24.04; set to ami-0fbcf351e82d18381 for byte-for-byte Phase 1 parity."
  type        = string
  default     = ""
}

variable "root_volume_size" {
  description = "Size (GiB) of the app host's gp3 root volume."
  type        = number
  default     = 30
}

variable "route53_zone_id" {
  description = "Hosted zone ID for link-shrink.org, referenced by the IAM policy for certbot's DNS-01 challenge. The zone itself is managed in Epic 6."
  type        = string
  default     = "Z05112061FM24VGB8BNP9"
}

variable "ecr_repositories" {
  description = "Service names to create ECR repositories for. Each becomes linkshrink-<name>."
  type        = list(string)
  default     = ["api", "redirect", "worker", "nginx", "migrate"]
}

variable "ecr_untagged_expire_days" {
  description = "Days after which untagged ECR images are expired to keep storage bounded."
  type        = number
  default     = 14
}
