# Root module outputs. Handy values for operators and for later epics to wire up
# (Epic 6's DNS A record points at public_ip; the zone/NS and ECR URLs land then).

output "instance_id" {
  description = "ID of the application host."
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Stable Elastic IP for link-shrink.org."
  value       = aws_eip.app.public_ip
}

output "security_group_id" {
  description = "ID of the edge security group."
  value       = aws_security_group.edge.id
}

output "iam_role_name" {
  description = "Name of the application host's IAM role."
  value       = aws_iam_role.ec2.name
}

output "instance_profile_name" {
  description = "Name of the application host's instance profile."
  value       = aws_iam_instance_profile.ec2.name
}

output "route53_zone_id" {
  description = "Hosted zone ID for link-shrink.org."
  value       = aws_route53_zone.main.zone_id
}

output "route53_name_servers" {
  description = "Zone nameservers — these must match what the registrar points at."
  value       = aws_route53_zone.main.name_servers
}

output "ecr_repository_urls" {
  description = "Map of service name to its ECR repository URL (for image push/pull)."
  value       = { for name, repo in aws_ecr_repository.app : name => repo.repository_url }
}
