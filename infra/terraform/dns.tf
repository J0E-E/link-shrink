# DNS for link-shrink.org. The hosted zone was created by hand in Phase 1 and is
# *imported* here, not recreated — recreating it would hand out new nameservers and
# break resolution until the registrar is updated:
#
#   terraform import aws_route53_zone.main Z05112061FM24VGB8BNP9
#
# The registrar's nameservers already point at this zone, so importing means no
# registrar change and no downtime.

resource "aws_route53_zone" "main" {
  name = var.domain

  tags = {
    Name      = var.domain
    Component = "dns"
  }
}

# Apex A record -> the stable Elastic IP from Epic 5. allow_overwrite lets apply
# adopt the existing hand-made record (same value) instead of erroring that it
# already exists.
resource "aws_route53_record" "apex" {
  zone_id         = aws_route53_zone.main.zone_id
  name            = var.domain
  type            = "A"
  ttl             = 300
  records         = [aws_eip.app.public_ip]
  allow_overwrite = true
}

# www -> the same Elastic IP as the apex. An A record (rather than a CNAME) keeps
# it in sync with the apex via the same aws_eip.app reference, and mirrors the
# apex record exactly. nginx canonicalises www -> apex; the TLS cert (cert.sh)
# must include www or the HTTPS handshake fails before that redirect is sent.
resource "aws_route53_record" "www" {
  zone_id         = aws_route53_zone.main.zone_id
  name            = "www.${var.domain}"
  type            = "A"
  ttl             = 300
  records         = [aws_eip.app.public_ip]
  allow_overwrite = true
}
