# IAM for the CI/CD pipeline — three least-privilege roles:
#   - codebuild  the build project: ECR push, logs, artifact bucket
#   - deploy     the deploy project: SSM Run Command to the host, logs, artifacts
#   - pipeline   CodePipeline itself: the connection, artifacts, starting builds

# ---------------------------------------------------------------------------
# Build project role
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "codebuild_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codebuild" {
  name               = "linkshrink-codebuild-role"
  description        = "LinkShrink build project role"
  assume_role_policy = data.aws_iam_policy_document.codebuild_trust.json

  tags = {
    Name      = "linkshrink-codebuild-role"
    Component = "cicd"
  }
}

data "aws_iam_policy_document" "codebuild" {
  # The ECR auth token is account-wide and cannot be resource-scoped.
  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Push/pull layers, scoped to the LinkShrink repositories only.
  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:DescribeImages",
    ]
    resources = [for repo in aws_ecr_repository.app : repo.arn]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.build.arn}:*"]
  }

  statement {
    sid     = "Artifacts"
    actions = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:GetBucketLocation"]
    resources = [
      aws_s3_bucket.artifacts.arn,
      "${aws_s3_bucket.artifacts.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "codebuild" {
  name   = "linkshrink-codebuild-inline"
  role   = aws_iam_role.codebuild.id
  policy = data.aws_iam_policy_document.codebuild.json
}

# ---------------------------------------------------------------------------
# Deploy project role
# ---------------------------------------------------------------------------

resource "aws_iam_role" "deploy" {
  name               = "linkshrink-deploy-role"
  description        = "LinkShrink deploy project role (SSM Run Command)"
  assume_role_policy = data.aws_iam_policy_document.codebuild_trust.json

  tags = {
    Name      = "linkshrink-deploy-role"
    Component = "cicd"
  }
}

data "aws_iam_policy_document" "deploy" {
  # SendCommand authorizes against BOTH the target instance and the document.
  statement {
    sid     = "SsmSendCommand"
    actions = ["ssm:SendCommand"]
    resources = [
      aws_instance.app.arn,
      "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
    ]
  }

  # GetCommandInvocation and DescribeInstances have no resource-level scoping.
  statement {
    sid       = "SsmRead"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
    resources = ["*"]
  }

  statement {
    sid       = "Ec2Describe"
    actions   = ["ec2:DescribeInstances"]
    resources = ["*"]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.deploy.arn}:*"]
  }

  # The deploy action still receives the source artifact and must read it.
  statement {
    sid     = "Artifacts"
    actions = ["s3:GetObject", "s3:GetObjectVersion", "s3:GetBucketLocation"]
    resources = [
      aws_s3_bucket.artifacts.arn,
      "${aws_s3_bucket.artifacts.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "linkshrink-deploy-inline"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}

# ---------------------------------------------------------------------------
# Pipeline role
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "pipeline_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codepipeline.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "pipeline" {
  name               = "linkshrink-pipeline-role"
  description        = "LinkShrink CodePipeline role"
  assume_role_policy = data.aws_iam_policy_document.pipeline_trust.json

  tags = {
    Name      = "linkshrink-pipeline-role"
    Component = "cicd"
  }
}

data "aws_iam_policy_document" "pipeline" {
  statement {
    sid       = "UseConnection"
    actions   = ["codestar-connections:UseConnection"]
    resources = [aws_codestarconnections_connection.github.arn]
  }

  statement {
    sid = "Artifacts"
    actions = [
      "s3:GetObject", "s3:GetObjectVersion", "s3:PutObject",
      "s3:GetBucketLocation", "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.artifacts.arn,
      "${aws_s3_bucket.artifacts.arn}/*",
    ]
  }

  statement {
    sid       = "StartBuilds"
    actions   = ["codebuild:StartBuild", "codebuild:BatchGetBuilds"]
    resources = [aws_codebuild_project.build.arn, aws_codebuild_project.deploy.arn]
  }
}

resource "aws_iam_role_policy" "pipeline" {
  name   = "linkshrink-pipeline-inline"
  role   = aws_iam_role.pipeline.id
  policy = data.aws_iam_policy_document.pipeline.json
}
