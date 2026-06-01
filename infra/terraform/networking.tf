# The edge security group: the only door into the box. HTTP and HTTPS from
# anywhere, nothing else. There is deliberately NO port 22 — administration is via
# SSM Session Manager (see iam.tf), so the instance never needs an open SSH port.
#
# Rules are separate resources (the provider 5.x idiom) so each is individually
# addressable and described, rather than packed into inline blocks.

resource "aws_security_group" "edge" {
  name        = "linkshrink-edge"
  description = "LinkShrink edge: HTTP/HTTPS only"
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name      = "linkshrink-edge"
    Component = "networking"
  }
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.edge.id
  description       = "HTTP from anywhere"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80

  tags = {
    Name      = "linkshrink-edge-http"
    Component = "networking"
  }
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.edge.id
  description       = "HTTPS from anywhere"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443

  tags = {
    Name      = "linkshrink-edge-https"
    Component = "networking"
  }
}

# Allow all outbound — the box pulls images, fetches packages, and answers
# certbot's DNS-01 challenge against Route 53.
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.edge.id
  description       = "All outbound traffic"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  tags = {
    Name      = "linkshrink-edge-egress"
    Component = "networking"
  }
}
