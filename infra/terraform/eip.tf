# The stable public IP for link-shrink.org. This allocation is carried over from
# the hand-built Phase 1 environment (imported, not recreated) so the domain keeps
# resolving across the rebuild:
#
#   terraform import aws_eip.app eipalloc-0c2d9d996302a32f0
#
# Keeping it separate from the instance means replacing the box re-binds the same
# IP instead of handing out a new one.

resource "aws_eip" "app" {
  domain = "vpc"

  tags = {
    Name      = "linkshrink-eip"
    Component = "networking"
  }

  # DNS depends on this exact IP — guard it against an accidental destroy. A full
  # `terraform destroy` will error here on purpose; use targeted destroys instead.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_eip_association" "app" {
  allocation_id = aws_eip.app.id
  instance_id   = aws_instance.app.id
}
