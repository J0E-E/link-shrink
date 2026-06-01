# The two CodeBuild projects the pipeline drives:
#   - build   tests + builds + pushes the six images to ECR (privileged: needs Docker)
#   - deploy  issues an SSM Run Command to roll the new images out on the host
#
# Both take their source from CodePipeline and log to their own CloudWatch group.

resource "aws_cloudwatch_log_group" "build" {
  name              = "/aws/codebuild/linkshrink-build"
  retention_in_days = 30

  tags = {
    Name      = "linkshrink-build-logs"
    Component = "cicd"
  }
}

resource "aws_cloudwatch_log_group" "deploy" {
  name              = "/aws/codebuild/linkshrink-deploy"
  retention_in_days = 30

  tags = {
    Name      = "linkshrink-deploy-logs"
    Component = "cicd"
  }
}

resource "aws_codebuild_project" "build" {
  name          = "linkshrink-build"
  description   = "Test, build, and push LinkShrink images to ECR"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 30

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec.yml"
  }

  artifacts {
    type = "CODEPIPELINE"
  }

  # privileged_mode runs the in-image Docker daemon (image builds + Testcontainers).
  environment {
    type            = "LINUX_CONTAINER"
    compute_type    = "BUILD_GENERAL1_MEDIUM"
    image           = var.codebuild_image
    privileged_mode = true
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.build.name
    }
  }

  tags = {
    Name      = "linkshrink-build"
    Component = "cicd"
  }
}

resource "aws_codebuild_project" "deploy" {
  name          = "linkshrink-deploy"
  description   = "Roll new images out to the host via SSM Run Command"
  service_role  = aws_iam_role.deploy.arn
  build_timeout = 20

  source {
    type      = "CODEPIPELINE"
    buildspec = "infra/deployspec.yml"
  }

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    type         = "LINUX_CONTAINER"
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = var.codebuild_image
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.deploy.name
    }
  }

  tags = {
    Name      = "linkshrink-deploy"
    Component = "cicd"
  }
}
