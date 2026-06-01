# Root module — no resources yet.
#
# Epic 4 delivers only the state backend and this skeleton, so `terraform plan`
# reports "no changes". Real resources arrive next:
#   - Epic 5: aws_instance (t3.medium) + user-data, security group (80/443, no 22),
#     Elastic IP, IAM role + instance profile.
#   - Epic 6: aws_route53_zone + apex A record, ECR repositories.
