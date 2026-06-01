# Root module index. Resources are grouped by concern in their own files:
#   - data.tf       account/VPC/subnet/AMI lookups
#   - networking.tf edge security group + rules
#   - iam.tf        instance role, policies, instance profile
#   - compute.tf    the t3.medium application host
#   - eip.tf        the stable Elastic IP (imported) + association
#   - dns.tf        the Route 53 zone (imported) + apex A record
#   - ecr.tf        the container image repositories + lifecycle policies
