# The application host: a single t3.medium running the whole compose stack
# (Postgres, Redis, the four app containers, nginx). It boots, installs Docker via
# cloud-init, and is reached only through SSM — there is no SSH key.

resource "aws_instance" "app" {
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default_az.ids[0]
  vpc_security_group_ids = [aws_security_group.edge.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  user_data = templatefile("${path.module}/user-data/cloud-init.yaml", {
    aws_region = var.aws_region
  })

  # IMDSv2 required, and a hop limit of 2 — the higher hop limit lets the certbot
  # and AWS CLI *containers* reach the metadata service across Docker's bridge.
  # Dropping this to 1 breaks certificate renewal.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name      = "linkshrink"
    Component = "compute"
  }

  # A newer Canonical AMI should never silently rebuild the live box. Replacement
  # stays a deliberate act (terraform apply -replace=aws_instance.app).
  lifecycle {
    ignore_changes = [ami]
  }
}
