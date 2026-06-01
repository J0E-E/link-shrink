# The instance's identity. It carries exactly the permissions the box needs and
# nothing more, so no static AWS keys ever live on the host:
#   - SSM core    -> Session Manager shell access (replaces SSH)
#   - ECR read    -> pull application images (used from Epic 7 on)
#   - inline      -> read app secrets from Parameter Store; answer certbot's
#                    Route 53 DNS-01 challenge, scoped to the LinkShrink zone

data "aws_iam_policy_document" "ec2_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2" {
  name               = "linkshrink-ec2-role"
  description        = "LinkShrink application host role"
  assume_role_policy = data.aws_iam_policy_document.ec2_trust.json

  tags = {
    Name      = "linkshrink-ec2-role"
    Component = "iam"
  }
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

data "aws_iam_policy_document" "inline" {
  # Read the app's secrets (hashids salt, Postgres/Redis credentials) — scoped to
  # this app's parameter prefix and this account.
  statement {
    sid     = "ReadAppSecrets"
    actions = ["ssm:GetParameter", "ssm:GetParametersByPath"]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/linkshrink/*"
    ]
  }

  # Find the hosted zone and poll a change's status — read-only, so scoped to "*".
  statement {
    sid       = "Route53List"
    actions   = ["route53:ListHostedZones", "route53:GetChange"]
    resources = ["*"]
  }

  # Write the DNS-01 challenge record — scoped to the LinkShrink zone only.
  statement {
    sid       = "Route53Change"
    actions   = ["route53:ChangeResourceRecordSets"]
    resources = ["arn:aws:route53:::hostedzone/${var.route53_zone_id}"]
  }
}

resource "aws_iam_role_policy" "inline" {
  name   = "linkshrink-inline"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.inline.json
}

# An instance profile is the wrapper EC2 needs to hand the role to the instance.
resource "aws_iam_instance_profile" "ec2" {
  name = "linkshrink-ec2-profile"
  role = aws_iam_role.ec2.name

  tags = {
    Name      = "linkshrink-ec2-profile"
    Component = "iam"
  }
}
